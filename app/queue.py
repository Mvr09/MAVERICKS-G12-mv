from datetime import timedelta
from sqlalchemy import select, or_, and_, func, text
from sqlalchemy.dialects.postgresql import insert
from app.models import (
    Job,
    Article,
    Batch,
    Grant,
    GrantArticle,
    ConsumptionBudget,
    Source,
    RssDailyUsage,
    Comparison,
    now,
)
from app.settings import RSS, settings


def analysis_key(article):
    return (
        "analysis:"
        + article.id
        + (f":g{article.generation}" if article.generation else "")
    )


def analysis_payload(article, profile="1.0.0"):
    from app.profiles import CANDIDATE_PROFILE
    data = {"article_id": article.id, "generation": article.generation, "analysis_profile": profile}
    if profile == CANDIDATE_PROFILE:
        from app.profiles import candidate_versions
        data["analysis_versions"] = candidate_versions()
    return data


def enqueue(db, key, kind, payload, priority=10):
    job = db.scalar(select(Job).where(Job.key == key))
    if job:
        return job
    job = Job(key=key, kind=kind, payload=payload, priority=priority)
    db.add(job)
    db.flush()
    return job


def reserve(db, article, split, manual_rss=False, fresh=False):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    if split == "rss" and not settings.rss_analysis_enabled and not manual_rss:
        return False
    existing = db.get(GrantArticle, article.id)
    daily_key = None
    if split == "rss":
        from app.importer import digest

        db.execute(text("SELECT pg_advisory_xact_lock(72642, 1)"))
        daily_key = digest(
            [now().date().isoformat(), article.origin_key, article.content_hash]
        )
        daily = db.scalar(
            select(func.count())
            .select_from(RssDailyUsage)
            .where(
                RssDailyUsage.reserved_at
                >= now().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        )
        if (
            not db.get(RssDailyUsage, daily_key)
            and daily >= RSS["daily_analysis_budget"]
        ):
            return False
    if existing and not fresh:
        old_grant = db.get(Grant, existing.grant_id)
        if (
            old_grant
            and (
                settings.jev_budget_limits_enabled
                or (old_grant.article_limit is None and old_grant.expires_at is None)
            )
            and (not old_grant.expires_at or old_grant.expires_at > now())
            and (not old_grant.budget_id or budget_available(db, old_grant.budget_id))
        ):
            if daily_key and not db.get(RssDailyUsage, daily_key):
                db.add(RssDailyUsage(id=daily_key))
                db.flush()
            return True
    query = select(Grant).where(Grant.split == split)
    if settings.jev_budget_limits_enabled:
        query = query.where(
            or_(Grant.article_limit == None, Grant.used < Grant.article_limit),
            or_(Grant.expires_at == None, Grant.expires_at > now()),
        )
    else:
        query = query.where(Grant.article_limit == None, Grant.expires_at == None)
    query = query.order_by(
        Grant.article_limit.is_not(None) if fresh else Grant.id, Grant.id
    ).with_for_update()
    grants = db.scalars(query).all()
    if not grants and not settings.jev_budget_limits_enabled:
        from app.cli import seed

        seed(db)
        db.flush()
        grants = db.scalars(query).all()
    grants = [g for g in grants if not g.budget_id or budget_available(db, g.budget_id)]
    if not grants:
        return False
    grant = grants[0]
    grant.used += 1
    if existing:
        existing.grant_id = grant.id
    else:
        db.add(GrantArticle(article_id=article.id, grant_id=grant.id))
    if daily_key and not db.get(RssDailyUsage, daily_key):
        db.add(RssDailyUsage(id=daily_key))
    db.flush()
    return True


def budget_available(db, budget_id):
    b = db.get(ConsumptionBudget, budget_id)
    return bool(
        b
        and (
            not settings.jev_budget_limits_enabled
            or b.request_limit is None
            or b.requests_used < b.request_limit
        )
        and (
            not settings.jev_budget_limits_enabled
            or not b.window_seconds
            or not b.started_at
            or now() < b.started_at + timedelta(seconds=b.window_seconds)
        )
    )


def enqueue_rss_analysis(db, limit=None, article_ids=None, profile="1.0.0"):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    query = select(Article).where(Article.context == "rss", Article.state == "pending")
    if article_ids is not None:
        query = query.where(Article.id.in_(article_ids))
    articles = db.scalars(query.order_by(Article.fetched_at.desc(), Article.id).with_for_update(skip_locked=True)).all()
    jobs = []
    for a in articles:
        if limit is not None and len(jobs) >= limit:
            break
        if db.scalar(select(Job).where(Job.key == analysis_key(a))):
            continue
        if reserve(db, a, "rss", manual_rss=True):
            jobs.append(
                enqueue(
                    db,
                    analysis_key(a),
                    "analysis",
                    analysis_payload(a, profile),
                    1,
                ).id
            )
    return jobs


def enqueue_batch(db, bid, profile="1.0.0"):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    b = db.get(Batch, bid)
    if not b:
        raise ValueError("Lote no encontrado")
    articles = db.scalars(
        select(Article)
        .where(Article.batch_id == bid)
        .order_by(Article.row_order)
        .with_for_update()
    ).all()
    from app.models import Analysis
    from app.profiles import CANDIDATE_PROFILE
    for a in articles:
        if a.state not in ("done", "review"):
            continue
        for old in db.scalars(select(Analysis).where(Analysis.article_id == a.id, Analysis.generation == a.generation)):
            if old.result.get("analysis_status") == "error":
                continue
            same = old.result.get("analysis_profile", old.result.get("question_version")) == profile
            if same and profile == CANDIDATE_PROFILE:
                from app.profiles import candidate_versions
                same = all(old.result.get("analysis_versions", {}).get(k) == v for k, v in candidate_versions().items())
            if not same:
                raise ValueError("Este lote contiene otro perfil o versión. Usa Reanalizar lote para una ejecución coherente, conservando el historial.")
    jobs = []
    for a in articles:
        if a.state in ("done", "review", "error"):
            continue
        if reserve(db, a, b.split):
            jobs.append(
                enqueue(
                    db,
                    analysis_key(a),
                    "analysis",
                    analysis_payload(a, profile),
                    100,
                ).id
            )
    if not jobs:
        raise ValueError(
            "El lote no tiene análisis pendientes para encolar. Usa Reanalizar para una ejecución nueva."
            if not settings.jev_budget_limits_enabled
            else "Sin presupuesto autorizado disponible para este lote. Los errores requieren diagnóstico y no se convierten en N."
        )
    if not b.started_at:
        b.started_at = now()
    db.flush()
    return jobs


def enqueue_sync(db, manual=False):
    db.execute(text("SELECT pg_advisory_xact_lock(72642, 3)"))
    jobs = []
    slot = (
        str(now().timestamp())
        if manual
        else str(int(now().timestamp()) // RSS["poll_seconds"])
    )
    for s in db.scalars(select(Source)):
        if s.data.get("enabled"):
            active = db.scalar(
                select(Job)
                .where(
                    Job.kind == "rss",
                    Job.state.in_(("queued", "running")),
                    Job.key.like(f"rss:{s.id}:%"),
                )
                .order_by(Job.id)
                .limit(1)
            )
            if active:
                jobs.append(active.id)
                continue
            jobs.append(
                enqueue(db, f"rss:{s.id}:{slot}", "rss", {"source_id": s.id}, 10).id
            )
    return jobs


def claim(db):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    exhausted = db.scalars(
        select(Job)
        .where(Job.state == "running", Job.lease_until < now(), Job.attempts >= 3)
        .with_for_update(skip_locked=True)
    ).all()
    for job in exhausted:
        job.state = "error"
        job.error = "LEASE_ATTEMPTS_EXHAUSTED"
        if job.kind == "campaign":
            from app.campaigns import fail_run
            fail_run(db,job.payload.get("run_id"),job.error)
        if job.kind == "comparison":
            row = db.get(Comparison, job.payload.get("comparison_id"))
            if row:
                row.state = "error"
                row.summary = {
                    **row.summary,
                    "message": "Lease agotado tras tres reclamaciones; requiere diagnóstico.",
                }
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
