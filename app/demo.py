"""Explicit presenter cleanup. No automatic reset and no consumption reset."""

from sqlalchemy import select, delete, text
from app.models import (
    Batch,
    Article,
    Analysis,
    Incident,
    Alert,
    Draft,
    Job,
    EvaluationLabel,
    GrantArticle,
)
from app.importer import digest
from app.auth import codec


def scope(db):
    batches = db.scalars(
        select(Batch).where(Batch.split.in_(["training", "liveday"])).order_by(Batch.id)
    ).all()
    bids = [b.id for b in batches]
    articles = db.scalars(
        select(Article).where(Article.batch_id.in_(bids)).order_by(Article.id)
    ).all()
    aids = {a.id for a in articles}
    jobs = [
        j
        for j in db.scalars(select(Job).where(Job.kind == "analysis"))
        if j.payload.get("article_id") in aids
    ]
    incidents = [
        i
        for i in db.scalars(select(Incident).where(Incident.context == "exercise"))
        if any(h.get("article_id") in aids for h in i.history)
    ]
    mixed = any(
        any(h.get("article_id") and h["article_id"] not in aids for h in i.history)
        for i in incidents
    )
    blocked = (
        "Hay análisis en curso; espera a que terminen."
        if any(j.state == "running" for j in jobs)
        else "Hay incidentes compartidos con otros lotes; la limpieza requiere revisión."
        if mixed
        else None
    )
    iids = [i.id for i in incidents]
    alerts = db.scalars(select(Alert).where(Alert.incident_id.in_(iids))).all()
    drafts = db.scalars(select(Draft).where(Draft.incident_id.in_(iids))).all()
    analyses = db.scalars(select(Analysis).where(Analysis.article_id.in_(aids))).all()
    snapshot = {
        "batches": [(b.id, b.file_hash) for b in batches],
        "articles": [(a.id, a.state) for a in articles],
        "jobs": sorted((j.id, j.state) for j in jobs),
        "incidents": sorted((i.id, i.revision) for i in incidents),
        "analyses": sorted(a.id for a in analyses),
        "alerts": sorted(a.id for a in alerts),
        "drafts": sorted(d.id for d in drafts),
    }
    counts = {
        "batches": len(bids),
        "articles": len(aids),
        "analyses": len(analyses),
        "incidents": len(iids),
        "alerts": len(alerts),
        "drafts": len(drafts),
    }
    return bids, aids, iids, jobs, snapshot, counts, blocked


def preview(db):
    *_, snapshot, counts, blocked = scope(db)
    return {
        "counts": counts,
        "blocked": blocked,
        "token": codec().dumps(
            {"purpose": "demo-cleanup", "snapshot": digest(snapshot)}
        ),
    }


def cleanup(db, token):
    # Shared by claims, imports and batch enqueueing; no new target job can start here.
    db.execute(text("SELECT pg_advisory_xact_lock(72642, 4)"))
    bids, aids, iids, jobs, snapshot, counts, blocked = scope(db)
    try:
        approved = codec().loads(token)
    except Exception:
        raise ValueError("Confirmación inválida. Vuelve a revisar la vista previa.")
    if approved != {"purpose": "demo-cleanup", "snapshot": digest(snapshot)}:
        raise ValueError("Los datos han cambiado. Vuelve a revisar la vista previa.")
    if blocked:
        raise ValueError(blocked)
    for model in (Draft, Alert):
        db.execute(delete(model).where(model.incident_id.in_(iids)))
    db.execute(delete(Incident).where(Incident.id.in_(iids)))
    db.execute(delete(Job).where(Job.id.in_([j.id for j in jobs])))
    for model in (EvaluationLabel, Analysis, GrantArticle):
        db.execute(delete(model).where(model.article_id.in_(aids)))
    db.execute(delete(Article).where(Article.id.in_(aids)))
    db.execute(delete(Batch).where(Batch.id.in_(bids)))
    # Keep ApiCall, RequestCache and Grant.used: deleting demo data never refunds budget.
    return counts
