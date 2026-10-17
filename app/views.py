from datetime import date
from sqlalchemy import select, func, and_
from app.models import (
    Supplier,
    Material,
    Article,
    Analysis,
    Incident,
    Source,
    Batch,
    now,
)


def current(incident):
    return max(
        (h for h in incident.history if "assessment" in h),
        key=lambda h: h.get("published_date", ""),
        default={},
    )


def article_view(db, a):
    result = db.scalar(
        select(Analysis)
        .where(Analysis.article_id == a.id)
        .order_by(Analysis.created_at.desc())
    )
    return {
        "id": a.id,
        "batch_id": a.batch_id,
        "state": a.state,
        "version": a.version,
        "fetched_at": a.fetched_at,
        "source_id": a.source_id,
        **a.data,
        "analysis": result.result if result else None,
        "cached": result.cached if result else False,
        "cache_stages": result.raw.get("_cache_stages", []) if result else [],
        "new_requests": result.raw.get("_new_requests") if result else None,
    }


def articles_view(db, context="exercise", include_history=False):
    query = select(Article).where(Article.context == context)
    if not include_history:
        latest = (
            select(Article.origin_key, func.max(Article.version).label("latest"))
            .group_by(Article.origin_key)
            .subquery()
        )
        query = query.join(
            latest,
            and_(
                Article.origin_key == latest.c.origin_key,
                Article.version == latest.c.latest,
            ),
        )
    articles = db.scalars(
        query.order_by(Article.fetched_at.desc(), Article.row_order)
    ).all()
    return [article_view(db, a) for a in articles]


def suppliers_view(db, context="exercise"):
    materials = [m.data for m in db.scalars(select(Material)).all()]
    incidents = db.scalars(select(Incident).where(Incident.context == context)).all()
    known = {}
    analyzed = db.execute(
        select(Article.data, Analysis.result)
        .join(Analysis, Analysis.article_id == Article.id)
        .where(Article.context == context)
    ).all()
    for article_data, result in analyzed:
        if result["analysis_status"] == "error":
            continue
        for assessment in result["assessments"]:
            if assessment["supplier_id"] not in result["affected_supplier_ids"]:
                continue
            sid = assessment["supplier_id"]
            stamp = article_data["published_date"]
            if sid not in known or stamp > known[sid]["date"]:
                known[sid] = {"date": stamp, "assessment": assessment}
    out = []
    for s in db.scalars(select(Supplier).order_by(Supplier.id)):
        hist = [i for i in incidents if i.supplier_id == s.id]
        active = [i for i in hist if i.state in ("active", "monitoring")]
        rows = [
            {
                "id": i.id,
                "state": i.state,
                "priority": i.priority,
                "historical_priority": i.historical_priority,
                "event_type": i.event_type,
                "event_date": i.event_date,
                "revision": i.revision,
                "history": i.history,
                "stale": (
                    now().date().isoformat() > i.event_date[:10]
                    and (now().date() - date.fromisoformat(i.event_date[:10])).days > 7
                )
                if context == "rss"
                else False,
            }
            for i in hist
        ]
        products = sorted(
            set(
                p
                for m in materials
                if s.id in (m["primary_id"], m["alternate_id"])
                for p in m["products"]
            )
        )
        latest = max(active, key=lambda i: i.priority, default=None)
        assessment = current(latest).get("assessment", {}) if latest else {}
        out.append(
            {
                **s.data,
                "products": products,
                "products_mapped": bool(products),
                "materials": [
                    m for m in materials if s.id in (m["primary_id"], m["alternate_id"])
                ],
                "priority": max(
                    (i.priority for i in active),
                    default=0 if hist or s.id in known else None,
                ),
                "urgent": any(
                    current(i).get("assessment", {}).get("urgent") == "Y"
                    for i in active
                ),
                "needs_review": any(
                    current(i).get("assessment", {}).get("needs_review") for i in active
                )
                or bool(
                    not hist
                    and known.get(s.id, {}).get("assessment", {}).get("needs_review")
                ),
                "incidents": rows,
                "incident_count": len(active),
                "latest_evidence": latest.event_date
                if latest
                else (
                    max(i.event_date for i in hist)
                    if hist
                    else known.get(s.id, {}).get("date")
                ),
                "reason": current(latest).get(
                    "explanation", "Sin incidentes analizados activos"
                )
                if latest
                else (
                    "Incidente recuperado; historial conservado"
                    if hist
                    else "Sin riesgo activo en las noticias procesadas"
                    if s.id in known
                    else "Pendiente de análisis"
                ),
                "status": "active"
                if active
                else (
                    "resolved" if hist else "positive" if s.id in known else "pending"
                ),
            }
        )
    return sorted(
        out,
        key=lambda s: (
            -(s["priority"] if s["priority"] is not None else -1),
            s["supplier_id"],
        ),
    )


def sources_view(db):
    return [
        {
            "id": s.id,
            **s.data,
            "status": s.status,
            "last_attempt_at": s.last_attempt_at,
            "last_success_at": s.last_success_at,
            "http_status": s.http_status,
            "item_count": s.item_count,
            "received_count": s.received_count,
            "duplicates": s.duplicates,
            "error_count": s.error_count,
            "error": s.error,
        }
        for s in db.scalars(select(Source).order_by(Source.id))
    ]
