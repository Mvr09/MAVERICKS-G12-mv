"""Selección explícita, vista previa firmada y operaciones transaccionales de demo."""

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
    ImportRow,
    Comparison,
    Supplier,
    Material,
    Source,
    now,
)
from app.importer import digest
from app.auth import codec

LABELS = {
    "training": "Entrenamiento",
    "validation": "Validación",
    "test": "Test",
    "liveday": "LiveDay",
}


def options(db):
    result = []
    for b in db.scalars(select(Batch).order_by(Batch.created_at)):
        count = len(
            db.scalars(select(Article.id).where(Article.batch_id == b.id)).all()
        )
        result.append(
            {
                "id": "batch:" + b.id,
                "label": f"{LABELS.get(b.split, b.split)} · {count} noticias · {b.created_at.date()}",
                "kind": "exercise",
                "count": count,
            }
        )
    for source in db.scalars(select(Source).order_by(Source.id)):
        count = len(
            db.scalars(
                select(Article.id).where(
                    Article.context == "rss", Article.source_id == source.id
                )
            ).all()
        )
        result.append(
            {
                "id": "rss:" + source.id,
                "label": source.data.get("name", source.id),
                "kind": "rss",
                "count": count,
            }
        )
    result.append(
        {
            "id": "catalog",
            "label": "Catálogo: proveedores y materiales",
            "kind": "catalog",
            "count": len(db.scalars(select(Supplier.id)).all()),
        }
    )
    return result


def scope(db, selection=None, mode="delete"):
    legacy = selection is None
    if legacy:
        selection = [
            "batch:" + b.id
            for b in db.scalars(
                select(Batch).where(Batch.split.in_(["training", "liveday"]))
            )
        ]
    selection = sorted(set(selection))
    allowed = {x["id"] for x in options(db)}
    individual = [s[8:] for s in selection if s.startswith("article:")]
    found = set(db.scalars(select(Article.id).where(Article.id.in_(individual))).all())
    if any(
        s not in allowed and not (s.startswith("article:") and s[8:] in found)
        for s in selection
    ):
        raise ValueError(
            "La selección contiene datos que ya no existen. Actualiza las opciones."
        )
    bids = [s[6:] for s in selection if s.startswith("batch:")]
    sources = [s[4:] for s in selection if s.startswith("rss:")]
    all_articles = db.scalars(select(Article).order_by(Article.id)).all()
    articles = [
        a
        for a in all_articles
        if a.batch_id in bids
        or a.id in individual
        or (a.context == "rss" and a.source_id in sources)
    ]
    if mode == "rerun":
        latest = {}
        for a in all_articles:
            latest[a.origin_key] = max(latest.get(a.origin_key, 0), a.version)
        articles = [
            a
            for a in articles
            if a.version == latest[a.origin_key] and a.state != "superseded"
        ]
    aids = {a.id for a in articles}
    jobs = [
        j
        for j in db.scalars(select(Job))
        if j.payload.get("article_id") in aids
        or (j.kind == "rss" and j.payload.get("source_id") in sources)
    ]
    incidents = [
        i
        for i in db.scalars(select(Incident))
        if any(h.get("article_id") in aids for h in i.history)
    ]
    if "catalog" in selection:
        incidents = db.scalars(select(Incident)).all()
    mixed = any(
        any(h.get("article_id") and h["article_id"] not in aids for h in i.history)
        for i in incidents
    )
    blocked = None
    if not selection:
        blocked = "Selecciona al menos una opción."
    elif any(j.state == "running" for j in jobs):
        blocked = "Hay trabajos en curso en la selección; espera a que terminen."
    elif legacy and mixed:
        blocked = (
            "Hay incidentes compartidos con otros lotes; la limpieza requiere revisión."
        )
    elif mode == "rerun" and (not articles or "catalog" in selection):
        blocked = (
            "Selecciona noticias o lotes para reanalizar; el catálogo no se analiza."
        )
    elif mode == "delete" and any(
        a.batch_id and a.batch_id not in bids and a.context == "exercise"
        for a in articles
    ):
        blocked = "Para borrar noticias de Excel elige su lote completo; puedes reanalizar una noticia sin borrarla."
    elif "catalog" in selection and len(aids) != len(all_articles):
        blocked = "Para borrar el catálogo selecciona también todas las noticias; hay resultados que lo necesitan."
    iids = [i.id for i in incidents]
    alerts = db.scalars(select(Alert).where(Alert.incident_id.in_(iids))).all()
    drafts = db.scalars(select(Draft).where(Draft.incident_id.in_(iids))).all()
    analyses = db.scalars(select(Analysis).where(Analysis.article_id.in_(aids))).all()
    comparisons = db.scalars(
        select(Comparison).where(Comparison.article_id.in_(aids))
    ).all()
    snapshot = {
        "selection": selection,
        "mode": mode,
        "articles": [(a.id, a.state, a.generation, a.content_hash) for a in articles],
        "jobs": sorted((j.id, j.state, j.attempts) for j in jobs),
        "incidents": sorted((i.id, i.revision, digest(i.history)) for i in incidents),
        "analyses": sorted((a.id, digest(a.result)) for a in analyses),
        "comparisons": sorted((c.id, c.state, digest(c.ballots)) for c in comparisons),
        "alerts": sorted((a.id, a.acknowledged, digest(a.data)) for a in alerts),
        "drafts": sorted((d.id, digest(d.text)) for d in drafts),
        "catalog_materials": [
            (m.id, digest(m.data))
            for m in db.scalars(select(Material).order_by(Material.id))
        ]
        if "catalog" in selection
        else [],
        "catalog": [
            (s.id, digest(s.data))
            for s in db.scalars(select(Supplier).order_by(Supplier.id))
        ]
        if "catalog" in selection
        else [],
    }
    counts = {
        "batches": len(bids),
        "articles": len(aids),
        "analyses": len(analyses),
        "incidents": len(iids),
        "alerts": len(alerts),
        "drafts": len(drafts),
        "comparisons": len(comparisons),
        "suppliers": len(db.scalars(select(Supplier.id)).all())
        if "catalog" in selection
        else 0,
        "materials": len(db.scalars(select(Material.id)).all())
        if "catalog" in selection
        else 0,
    }
    return {
        "selection": selection,
        "mode": mode,
        "articles": articles,
        "aids": aids,
        "bids": bids,
        "sources": sources,
        "incidents": incidents,
        "jobs": jobs,
        "snapshot": snapshot,
        "counts": counts,
        "blocked": blocked,
        "legacy": legacy,
    }


def preview(db, selection=None, mode="delete"):
    plan = scope(db, selection, mode)
    return {
        "counts": plan["counts"],
        "blocked": plan["blocked"],
        "mode": mode,
        "maximum_requests": len(plan["aids"]) * 6 if mode == "rerun" else 0,
        "token": codec().dumps(
            {
                "purpose": "demo-cleanup",
                "selection": None if plan["legacy"] else plan["selection"],
                "mode": mode,
                "snapshot": digest(plan["snapshot"]),
                "issued_at": now().timestamp(),
            }
        ),
    }


def detach_incidents(db, incidents, aids):
    """Retira solo las evidencias elegidas y recalcula incidentes compartidos."""
    for inc in incidents:
        retained = [h for h in inc.history if h.get("article_id") not in aids]
        evidence = [h for h in retained if h.get("assessment")]
        # Borradores y alertas dependen de la revisión de evidencia anterior.
        for model in (Draft, Alert):
            db.execute(delete(model).where(model.incident_id == inc.id))
        if not evidence:
            db.delete(inc)
            continue
        current = max(
            evidence, key=lambda h: (h.get("published_date", ""), h.get("at", ""))
        )
        assessment = current["assessment"]
        manual = [h for h in retained if h.get("manual")]
        manually_resolved = bool(
            manual and max(h.get("at", "") for h in manual) > current.get("at", "")
        )
        impact = assessment["impact_status"]
        inc.state = (
            "resolved"
            if manually_resolved or impact == "resolved"
            else impact
            if impact in ("active", "monitoring")
            else "monitoring"
        )
        inc.priority = 0 if inc.state == "resolved" else assessment.get("priority") or 0
        inc.historical_priority = max(
            (h["assessment"].get("priority") or 0 for h in evidence), default=0
        )
        inc.event_date = current["published_date"]
        inc.history = retained
        inc.revision += 1
        # Regenerar aviso visual si sigue siendo necesario; no emitir audio por una limpieza.
        if inc.state != "resolved" and (
            assessment.get("urgent") == "Y"
            or assessment.get("needs_review")
            or assessment.get("priority_band") == "critical"
        ):
            db.add(
                Alert(
                    incident_id=inc.id,
                    revision=inc.revision,
                    data={
                        "supplier_id": inc.supplier_id,
                        "supplier_name": db.get(Supplier, inc.supplier_id).data["name"],
                        "priority": inc.priority,
                        "headline": current.get("headline", ""),
                        "needs_review": assessment.get("needs_review", True),
                        "sound_eligible": False,
                        "state": inc.state,
                        "article_id": current.get("article_id"),
                    },
                )
            )
    db.flush()


def cleanup(db, token):
    db.execute(text("SELECT pg_advisory_xact_lock(72642, 4)"))
    try:
        approved = codec().loads(token)
        if (
            approved.get("purpose") != "demo-cleanup"
            or now().timestamp() - approved["issued_at"] > 900
        ):
            raise ValueError()
        plan = scope(db, approved["selection"], approved["mode"])
    except Exception:
        raise ValueError(
            "Confirmación inválida o caducada. Vuelve a revisar la vista previa."
        )
    if approved["snapshot"] != digest(plan["snapshot"]):
        raise ValueError("Los datos han cambiado. Vuelve a revisar la vista previa.")
    if plan["blocked"]:
        raise ValueError(plan["blocked"])
    aids = plan["aids"]
    if plan["mode"] == "rerun":
        from app.queue import reserve, enqueue
        from app.jev import grant_requires_diagnosis

        # Autorizar todo antes de retirar resultados; fallo revierte la transacción completa.
        for a in plan["articles"]:
            old = db.get(GrantArticle, a.id)
            if old and grant_requires_diagnosis(db, old.grant_id):
                raise ValueError("Hay un error de proveedor pendiente de diagnóstico.")
            split = db.get(Batch, a.batch_id).split if a.batch_id else "rss"
            if not reserve(db, a, split, manual_rss=True, fresh=True):
                raise ValueError(
                    "No hay autorización disponible para toda la selección."
                )
            reservation = db.get(GrantArticle, a.id)
            if grant_requires_diagnosis(db, reservation.grant_id):
                raise ValueError(
                    "Hay un error de proveedor pendiente de diagnóstico; no se reinician sus intentos."
                )
        detach_incidents(db, plan["incidents"], aids)
        # Cancelar trabajos pendientes anteriores para no duplicar ni publicar generaciones antiguas.
        for j in plan["jobs"]:
            if j.kind != "rss" and j.state == "queued":
                j.state = "cancelled"
                if j.kind == "comparison":
                    comparison = db.get(Comparison, j.payload.get("comparison_id"))
                    if comparison:
                        comparison.state = "cancelled"
        job_ids = []
        for a in plan["articles"]:
            a.generation += 1
            a.state = "pending"
            job_ids.append(
                enqueue(
                    db,
                    f"analysis:{a.id}:g{a.generation}",
                    "analysis",
                    {"article_id": a.id, "generation": a.generation},
                    100,
                ).id
            )
            if a.batch_id:
                batch = db.get(Batch, a.batch_id)
                batch.started_at = now()
                batch.completed_at = None
        return {**plan["counts"], "job_ids": job_ids, "mode": "rerun"}
    detach_incidents(db, plan["incidents"], aids)
    db.execute(
        delete(Job).where(Job.id.in_([j.id for j in plan["jobs"] if j.kind != "rss"]))
    )
    for model in (Comparison, EvaluationLabel, Analysis, GrantArticle, ImportRow):
        db.execute(delete(model).where(model.article_id.in_(aids)))
    db.execute(delete(Article).where(Article.id.in_(aids)))
    db.execute(delete(Batch).where(Batch.id.in_(plan["bids"])))
    # Si se borra una noticia individual, conservar el lote y corregir su contador.
    for batch in db.scalars(select(Batch)):
        batch.count = len(
            db.scalars(select(Article.id).where(Article.batch_id == batch.id)).all()
        )
    for sid in set(plan["sources"]) | {
        a.source_id for a in plan["articles"] if a.context == "rss" and a.source_id
    }:
        source = db.get(Source, sid)
        source.etag = source.modified = None
        source.status = "pending"
        source.last_success_at = None
        source.http_status = None
        source.item_count = 0
    if "catalog" in plan["selection"]:
        db.execute(delete(Draft))
        db.execute(delete(Alert))
        db.execute(delete(Incident))
        db.execute(delete(Material))
        db.execute(delete(Supplier))
    # ApiCall, RequestCache, Grant.used y budgets conservan el historial de consumo.
    return {**plan["counts"], "mode": "delete"}
