"""Tres consultas del mismo JEV: contraste auxiliar, nunca una nueva certeza."""

from collections import Counter
from sqlalchemy import select, text, func
from app.models import Article, Comparison, Job, GrantArticle, ApiCall
from app.queue import reserve, enqueue
from app.jev import grant_requires_diagnosis
from app.importer import digest


def summarize(ballots):
    counts = Counter(b["analysis_status"] for b in ballots)
    signatures = Counter(
        digest(
            {
                "risk": b["is_risk"],
                "urgent": b["urgent"],
                "suppliers": b["affected_supplier_ids"],
                "event": b["event_type"],
            }
        )
        for b in ballots
        if b["analysis_status"] != "error"
    )
    reasons = sorted(
        {r for b in ballots for r in b.get("review_reasons", [])}
        | {
            r
            for b in ballots
            for a in b.get("assessments", [])
            for r in a.get("review_reasons", [])
        }
    )
    majority = counts["done"] >= 2
    return {
        "completed": len(ballots),
        "done_votes": counts["done"],
        "review_votes": counts["review"],
        "errors": counts["error"],
        "decision_agreement": max(signatures.values(), default=0),
        "majority_without_review": majority,
        "review_reasons": reasons,
        "advisory_only": True,
        "message": "Dos o más evaluaciones no requieren revisión según la política; contrasta también sus decisiones y evidencias."
        if majority
        else "La mayoría sigue sin una conclusión suficiente para retirar la revisión.",
        "limitation": "Tres consultas al mismo modelo no son tres expertos independientes. No cambian el análisis vigente, la prioridad, las alarmas ni las exportaciones.",
    }


def enqueue_comparison(db, aid):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    article = db.scalar(select(Article).where(Article.id == aid).with_for_update())
    if not article or article.context != "rss":
        raise ValueError("El contraste está disponible únicamente para noticias RSS.")
    if article.state not in ("review", "done"):
        raise ValueError("Completa primero el análisis de la noticia.")
    active = db.scalar(
        select(Comparison).where(
            Comparison.article_id == aid, Comparison.state.in_(["queued", "running"])
        )
    )
    if active:
        job = db.scalar(select(Job).where(Job.key == "comparison:" + active.id))
        return active, job
    old = db.get(GrantArticle, aid)
    if old and grant_requires_diagnosis(db, old.grant_id):
        raise ValueError("El proveedor requiere diagnóstico antes de otra consulta.")
    if not reserve(db, article, "rss", manual_rss=True, fresh=True):
        raise ValueError("Sin autorización de consumo disponible.")
    comparison = Comparison(article_id=aid)
    db.add(comparison)
    db.flush()
    job = enqueue(
        db,
        "comparison:" + comparison.id,
        "comparison",
        {
            "article_id": aid,
            "comparison_id": comparison.id,
            "generation": article.generation,
        },
        10,
    )
    return comparison, job


def process_comparison(db, cid, transport=None):
    from app.analysis import process_article

    comparison = db.get(Comparison, cid)
    if comparison.state in ("done", "error", "cancelled"):
        return comparison
    comparison.state = "running"
    db.commit()
    # Guardar cada voto: reclamar un lease no repite consultas ya completadas.
    while len(comparison.ballots) < 3:
        index = len(comparison.ballots)
        result = process_article(
            db,
            comparison.article_id,
            transport=transport,
            run_key=f"comparison:{cid}:{index}",
            publish=False,
        )
        comparison.ballots = [*comparison.ballots, result]
        comparison.summary = summarize(comparison.ballots)
        if result["analysis_status"] == "error":
            comparison.state = "error"
            db.commit()
            return comparison
        db.commit()
    comparison.state = "done"
    db.commit()
    return comparison


def view(db, row):
    return {
        "id": row.id,
        "article_id": row.article_id,
        "network_requests": db.scalar(
            select(func.count())
            .select_from(ApiCall)
            .where(
                ApiCall.article_id == row.article_id,
                ApiCall.run_key.like("comparison:" + row.id + ":%"),
            )
        ),
        "state": row.state,
        "created_at": row.created_at,
        "ballots": [
            {
                "analysis_status": b["analysis_status"],
                "is_risk": b["is_risk"],
                "urgent": b["urgent"],
                "affected_supplier_ids": b["affected_supplier_ids"],
                "event_type": b["event_type"],
                "event_classification": b.get("event_classification"),
                "error": b["error"],
                "review_reasons": sorted(
                    set(b["review_reasons"])
                    | {r for a in b["assessments"] for r in a["review_reasons"]}
                ),
                "model_id": b["model_id"],
            }
            for b in row.ballots
        ],
        "summary": row.summary,
    }
