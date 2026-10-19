from datetime import date
from app.provenance import KNOWN_INPUT_FILENAMES
from app.event_tags import event_tag
from app.geography import payload_location
from app.settings import POLICY
from sqlalchemy import select, func, and_
from app.models import (
    Supplier,
    Material,
    Article,
    Analysis,
    Incident,
    Source,
    Job,
    Batch,
    now,
)


def current(incident):
    return max(
        (h for h in incident.history if "assessment" in h and not h.get("superseded")),
        key=lambda h: (h.get("published_date", ""), h.get("at", "")),
        default={},
    )


def batch_label(batch):
    labels = {
        "training": "Entrenamiento",
        "validation": "Validación",
        "test": "Test",
        "liveday": "LiveDay",
    }
    return (
        batch.filename
        or KNOWN_INPUT_FILENAMES.get(batch.file_hash)
        or labels.get(batch.split, batch.split) + " · nombre de archivo no registrado"
    )


def origin_matches(article, origin):
    return not origin or origin == (
        "batch:" + article.batch_id
        if article.batch_id
        else "rss:" + (article.source_id or "")
    )


def article_view(db, a):
    result = db.scalar(
        select(Analysis)
        .where(Analysis.article_id == a.id, Analysis.generation == a.generation)
        .order_by(Analysis.created_at.desc())
    )
    return {
        "id": a.id,
        "batch_id": a.batch_id,
        "origin": "batch:" + a.batch_id if a.batch_id else "rss:" + (a.source_id or ""),
        "origin_label": batch_label(db.get(Batch, a.batch_id))
        if a.batch_id
        else a.data.get("source", "RSS"),
        "split": db.get(Batch, a.batch_id).split if a.batch_id else "rss",
        "state": a.state,
        "version": a.version,
        "generation": a.generation,
        "fetched_at": a.fetched_at,
        "source_id": a.source_id,
        "preliminary_relevance": __import__("app.relevance",fromlist=["preliminary"]).preliminary(db,a) if a.context == "rss" else None,
        **a.data,
        "analysis": result.result if result else None,
        "human_review": __import__("app.human_review",fromlist=["summary"]).summary(db,a,result) if result else None,
        "event_type_confidence": result.raw.get("a", {})
        .get("answers", {})
        .get("event_type", {})
        .get("confidence")
        if result
        else None,
        "cached": result.cached if result else False,
        "cache_stages": result.raw.get("_cache_stages", []) if result else [],
        "new_requests": result.raw.get("_new_requests") if result else None,
    }


def articles_view(db, context="exercise", include_history=False, origin=""):
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
    return [article_view(db, a) for a in articles if origin_matches(a, origin)]


def suppliers_view(db, context="exercise", origin=""):
    materials = [m.data for m in db.scalars(select(Material)).all()]
    incidents = db.scalars(select(Incident).where(Incident.context == context)).all()
    if origin:
        from types import SimpleNamespace

        selected_ids = {
            a.id
            for a in db.scalars(select(Article).where(Article.context == context))
            if origin_matches(a, origin)
        }
        projected = []
        for inc in incidents:
            history = [h for h in inc.history if h.get("article_id") in selected_ids and not h.get("superseded")]
            if not history:
                continue
            entry = max(
                history, key=lambda h: (h.get("published_date", ""), h.get("at", ""))
            )
            assessment = entry.get("assessment", {})
            state = (
                "resolved"
                if inc.state == "resolved"
                or assessment.get("impact_status") == "resolved"
                else assessment.get("impact_status", inc.state)
            )
            projected.append(
                SimpleNamespace(
                    id=inc.id,
                    supplier_id=inc.supplier_id,
                    history=history,
                    state=state,
                    priority=0
                    if state == "resolved"
                    else assessment.get("priority", 0),
                    historical_priority=max(
                        (h.get("assessment", {}).get("priority") or 0 for h in history),
                        default=0,
                    ),
                    event_type=inc.event_type,
                    event_date=entry.get("published_date", inc.event_date),
                    revision=inc.revision,
                )
            )
        incidents = projected
    from app.models import IncidentWork
    work_by_incident = {}
    for work in db.scalars(select(IncidentWork).order_by(IncidentWork.created_at.desc(),IncidentWork.id.desc())):
        work_by_incident.setdefault(work.incident_id,{k:work.data.get(k) for k in ("status","action","due_date")})
    known = {}
    doubts = {}
    processed = 0
    human_pending = set()
    review_work = {}
    analyzed = db.execute(
        select(Article, Analysis.result)
        .join(Analysis, Analysis.article_id == Article.id)
        .where(Article.context == context, Analysis.generation == Article.generation)
        .order_by(Analysis.created_at)
    ).all()
    analyzed = list({article_row.id: (article_row, result) for article_row, result in analyzed}.values())
    article_tags = {a.id: event_tag(result) for a, result in analyzed}
    for article_row, result in analyzed:
        if not origin_matches(article_row, origin):
            continue
        from app.human_review import effective_result
        result = effective_result(db, article_row, result)
        article_data = article_row.data
        if result["analysis_status"] == "error":
            continue
        from app.human_review import current_decisions
        human_pending.update(sid for sid,r in current_decisions(db,article_row).items() if r.data["association"] == "unknown")
        processed += 1
        uncertain_links = {d["supplier_id"] for d in result.get("review_details", []) if d["requires_review"] and d["relevance"] == "association"}
        for assessment in result["assessments"]:
            sid = assessment["supplier_id"]
            if assessment.get("needs_review") and (sid in uncertain_links or assessment["p_link"] >= POLICY["thresholds"]["review_low"]):
                doubts[sid] = article_data["published_date"]
                review_work.setdefault(sid,[]).append({"article_id":article_row.id,"headline":article_data["headline"]})
            if sid not in result["affected_supplier_ids"]:
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
                "current_headline": current(i).get("headline"),
                "procurement_work": work_by_incident.get(i.id),
                "event_tag": current(i).get("event_tag")
                or article_tags.get(current(i).get("article_id")),
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
                "geography": payload_location({}, s.data),
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
                "needs_review": s.id in doubts or s.id in human_pending or any(
                    current(i).get("assessment", {}).get("needs_review") for i in active
                )
                or bool(not active and s.id in doubts)
                or bool(not hist and known.get(s.id, {}).get("assessment", {}).get("needs_review")),
                "incidents": rows,
                "review_work": review_work.get(s.id, []),
                "incident_count": len(active),
                "latest_evidence": latest.event_date
                if latest
                else (
                    max(i.event_date for i in hist)
                    if hist
                    else known.get(s.id, {}).get("date") or doubts.get(s.id)
                ),
                "reason": current(latest).get(
                    "explanation", "Sin incidentes analizados activos"
                )
                if latest
                else (
                    "Hay dudas de exposición o decisión que requieren verificación"
                    if s.id in doubts
                    else "Incidente recuperado; historial conservado"
                    if any(i.state == "resolved" for i in hist)
                    else "Análisis anterior sustituido; consulta el último resultado"
                    if hist
                    else "Sin riesgo activo en las noticias procesadas"
                    if s.id in known
                    else "Sin vínculo sustentado en las noticias procesadas"
                    if processed
                    else "Pendiente de análisis"
                ),
                "status": "active"
                if active
                else (
                    "review" if s.id in doubts else "resolved" if any(i.state == "resolved" for i in hist)
                    else "superseded" if hist else "positive" if s.id in known else "unlinked" if processed else "pending"
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
    latest = {}
    source_key = Job.payload["source_id"].as_string()
    for j in db.scalars(
        select(Job)
        .where(Job.kind == "rss")
        .distinct(source_key)
        .order_by(source_key, Job.next_attempt_at.desc(), Job.id.desc())
    ):
        latest.setdefault(j.payload.get("source_id"), j)
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
            "job_state": latest[s.id].state if s.id in latest else None,
        }
        for s in db.scalars(select(Source).order_by(Source.id))
    ]
