"""Modelo: calidad supervisada y telemetría registrada, sin ejecutar JEV."""

from collections import Counter
from sqlalchemy import select
from app.models import Article, Analysis, Batch, ApiCall, Job, Comparison, now
from app.views import origin_matches, batch_label
from app.evaluation import evaluate_batch, ratio
from app.settings import settings, POLICY
from app.rss_questions import VERSION


def percentiles(values):
    values = sorted(values)

    def quantile(q):
        if not values:
            return None
        position = (len(values) - 1) * q
        lower = int(position)
        fraction = position - lower
        return values[lower] + fraction * (
            values[min(lower + 1, len(values) - 1)] - values[lower]
        )

    return {"n": len(values), "p50": quantile(0.5), "p95": quantile(0.95)}


def model_metrics(db, context, origin=""):
    articles = [
        a
        for a in db.scalars(select(Article).where(Article.context == context))
        if origin_matches(a, origin)
    ]
    retained_ids = {a.id for a in articles}
    current_articles = {}
    for article in articles:
        if (
            article.origin_key not in current_articles
            or article.version > current_articles[article.origin_key].version
        ):
            current_articles[article.origin_key] = article
    by_id = {a.id: a for a in current_articles.values()}
    aids = set(by_id)
    latest = {}
    for analysis in db.scalars(
        select(Analysis)
        .where(Analysis.article_id.in_(aids))
        .order_by(Analysis.created_at.desc())
    ):
        if analysis.generation == by_id[analysis.article_id].generation:
            latest.setdefault(analysis.article_id, analysis)
    calls = db.scalars(
        select(ApiCall).where(ApiCall.article_id.in_(retained_ids))
    ).all()
    jobs = db.scalars(select(Job).where(Job.kind.in_(["analysis", "comparison"]))).all()
    jobs = [
        j
        for j in jobs
        if j.payload.get("article_id") in aids
        and j.payload.get("generation", 0) == by_id[j.payload["article_id"]].generation
    ]
    usage = {
        key: sum(
            c.usage[key] for c in calls if isinstance(c.usage.get(key), (int, float))
        )
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    agreement = []
    seen = set()
    comparison_jobs = {
        j.payload.get("comparison_id"): j for j in jobs if j.kind == "comparison"
    }
    for row in db.scalars(
        select(Comparison)
        .where(Comparison.article_id.in_(aids))
        .order_by(Comparison.created_at.desc())
    ):
        if (
            row.article_id in seen
            or row.id not in comparison_jobs
            or row.state != "done"
            or len(row.ballots) != 3
            or any(b["analysis_status"] == "error" for b in row.ballots)
        ):
            continue
        profiles = {
            (b["model_id"], b["question_version"], b["policy_version"])
            for b in row.ballots
        }
        if len(profiles) != 1:
            continue
        seen.add(row.article_id)
        agreement.append(row.summary.get("decision_agreement", 0))
    versions = Counter(
        (
            a.result.get("model_id"),
            a.result["question_version"],
            a.result["policy_version"],
            a.result.get("analysis_versions", {}).get("review", a.result.get("review_policy_version", "no registrada")),
        )
        for a in latest.values()
    )
    quality = []
    for batch in db.scalars(select(Batch).order_by(Batch.created_at)):
        item = {
            "id": batch.id,
            "split": batch.split,
            "label": batch_label(batch),
            "count": batch.count,
            "status": "unlabelled",
            "metrics": None,
        }
        if batch.split in ("training", "validation"):
            try:
                item.update(status="evaluated", metrics=evaluate_batch(db, batch.id))
            except ValueError as exc:
                item.update(status="unavailable", reason=str(exc))
        else:
            item["reason"] = (
                "Sin etiquetas de referencia; las columnas de respuesta vacías no son resultados correctos."
            )
        quality.append(item)
    return {
        "updated_at": now(),
        "context": context,
        "origin": origin,
        "configured_model": settings.jev_model,
        "exercise_question_version": POLICY["question_version"],
        "rss_question_version": VERSION,
        "policy_version": POLICY["version"],
        "evaluations": quality,
        "execution": {
            "article_count": len(aids),
            "retained_article_versions": len(articles),
            "latest_analysis_count": len(latest),
            "analysis_latency": percentiles([a.duration for a in latest.values()]),
            "http_latency": percentiles(
                [
                    c.duration
                    for c in calls
                    if c.status is not None or c.usage.get("_error")
                ]
            ),
            "requests": len(calls),
            "retries": sum(c.attempt > 1 for c in calls),
            "failed_requests": sum(
                (c.status is not None and c.status != 200)
                or bool(c.usage.get("_error"))
                for c in calls
            ),
            "inflight_requests": sum(
                c.status is None and not c.usage.get("_error") for c in calls
            ),
            "cache_hits": sum(a.cached for a in latest.values()),
            "usage": usage,
            "calls_with_token_usage": sum(
                any(
                    isinstance(c.usage.get(k), (int, float))
                    for k in ("input_tokens", "output_tokens", "total_tokens")
                )
                for c in calls
            ),
            "http_statuses": [
                {"status": str(k) if k is not None else "sin respuesta", "count": v}
                for k, v in sorted(
                    Counter(c.status for c in calls).items(), key=lambda x: str(x[0])
                )
            ],
            "jobs": dict(Counter(j.state for j in jobs)),
            "versions": [
                {"model": m, "questions": q, "policy": p, "review": r, "count": n}
                for (m, q, p, r), n in sorted(versions.items(), key=lambda x: str(x[0]))
            ],
            "consistency": {
                "articles": len(agreement),
                "unanimous": sum(n == 3 for n in agreement),
                "unanimous_rate": ratio(sum(n == 3 for n in agreement), len(agreement)),
                "accuracy_claim": False,
            },
            "scope_note": "Peticiones de las noticias conservadas del origen, incluidas generaciones anteriores y contrastes. Latencia de análisis: generación vigente, sin espera en cola. No incluye noticias borradas. Uso reportado; sin estimación de coste.",
        },
    }
