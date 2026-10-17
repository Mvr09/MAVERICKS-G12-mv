from datetime import timedelta
from sqlalchemy import select, or_, and_, func, text
from sqlalchemy.dialects.postgresql import insert
from app.models import Job, Article, Batch, Grant, GrantArticle, Source, now
from app.settings import RSS, settings


def enqueue(db, key, kind, payload, priority=10):
    job = db.scalar(select(Job).where(Job.key == key))
    if job:
        return job
    job = Job(key=key, kind=kind, payload=payload, priority=priority)
    db.add(job)
    db.flush()
    return job


def reserve(db, article, split):
    if db.get(GrantArticle, article.id):
        return True
    if split == "rss" and not settings.rss_analysis_enabled:
        return False
    if split == "rss":
        db.execute(text("SELECT pg_advisory_xact_lock(72642, 1)"))
        daily = db.scalar(
            select(func.count())
            .select_from(GrantArticle)
            .join(Article)
            .where(
                Article.context == "rss",
                GrantArticle.reserved_at
                >= now().replace(hour=0, minute=0, second=0, microsecond=0),
            )
        )
        if daily >= RSS["daily_analysis_budget"]:
            return False
    grants = db.scalars(
        select(Grant)
        .where(
            Grant.split == split,
            Grant.used < Grant.article_limit,
            or_(Grant.expires_at == None, Grant.expires_at > now()),
        )
        .order_by(Grant.id)
        .with_for_update()
    ).all()
    if not grants:
        return False
    grant = grants[0]
    grant.used += 1
    db.add(GrantArticle(article_id=article.id, grant_id=grant.id))
    db.flush()
    return True


def enqueue_batch(db, bid):
    b = db.get(Batch, bid)
    if not b:
        raise ValueError("Lote no encontrado")
    articles = db.scalars(
        select(Article)
        .where(Article.batch_id == bid)
        .order_by(Article.row_order)
        .with_for_update()
    ).all()
    jobs = []
    for a in articles:
        if a.state in ("done", "review"):
            continue
        if reserve(db, a, b.split):
            jobs.append(
                enqueue(
                    db, "analysis:" + a.id, "analysis", {"article_id": a.id}, 100
                ).id
            )
    if not jobs:
        raise ValueError(
            "Sin presupuesto autorizado disponible para este lote. Los errores requieren diagnóstico y no se convierten en N."
        )
    if not b.started_at:
        b.started_at = now()
    db.flush()
    return jobs


def enqueue_sync(db, manual=False):
    jobs = []
    slot = (
        str(now().timestamp())
        if manual
        else str(int(now().timestamp()) // RSS["poll_seconds"])
    )
    for s in db.scalars(select(Source)):
        if s.data.get("enabled"):
            jobs.append(
                enqueue(db, f"rss:{s.id}:{slot}", "rss", {"source_id": s.id}, 10).id
            )
    return jobs


def claim(db):
    exhausted = db.scalars(
        select(Job)
        .where(Job.state == "running", Job.lease_until < now(), Job.attempts >= 3)
        .with_for_update(skip_locked=True)
    ).all()
    for job in exhausted:
        job.state = "error"
        job.error = "LEASE_ATTEMPTS_EXHAUSTED"
        job.lease_until = None
    # Locking is transactional across independent worker processes.
    expired = and_(Job.state == "running", Job.lease_until < now())
    j = db.scalar(
        select(Job)
        .where(
            or_(Job.state == "queued", expired),
            Job.next_attempt_at <= now(),
            Job.attempts < 3,
        )
        .order_by(Job.priority.desc(), Job.next_attempt_at, Job.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not j:
        return None
    j.state = "running"
    j.attempts += 1
    j.heartbeat = now()
    j.lease_until = now() + timedelta(seconds=90)
    db.flush()
    return j
