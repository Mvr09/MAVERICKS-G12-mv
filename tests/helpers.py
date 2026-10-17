from datetime import datetime, timezone
from app.models import Article, Batch
from app.importer import digest


def synthetic(
    db,
    headline="Synthetic factory fire affects S001 and S002",
    summary="Synthetic event: a fire halts production for 14 days.",
    published="2026-10-01T12:00:00+00:00",
):
    data = {
        "news_id": "SYNTHETIC-TEST",
        "headline": headline,
        "summary": summary,
        "published_date": published,
        "source": "MOCK IDENTIFICADO",
        "context_id": "exercise",
        "language": "en",
    }
    batch = Batch(
        file_hash=digest([data, datetime.now(timezone.utc).isoformat()]),
        split="training",
        count=1,
        logical_date=published,
    )
    db.add(batch)
    db.flush()
    a = Article(
        origin_key=batch.id,
        context="exercise",
        news_id=data["news_id"],
        batch_id=batch.id,
        data=data,
        content_hash=digest(data),
    )
    db.add(a)
    db.commit()
    return a


def answer(
    payload,
    linked=("S001", "S002"),
    risk=0.96,
    urgent=0.95,
    impact="active",
    event="fire_incident",
    confidence=0.95,
):
    out = {}
    for key, q in payload["questions"].items():
        kind = q["type"]
        if kind == "noul":
            sid = key.rsplit("_", 1)[-1]
            value = (
                (0.98 if sid in linked else 0.02)
                if key.startswith("linked_")
                else (risk if key.startswith("risk_") else urgent)
            )
            out[key] = {"type": kind, "noul": value}
        else:
            criteria = q["criteria"]
            keys = (
                list(criteria)
                if kind == "choice"
                else [str(i) for i in range(len(criteria))]
            )
            choice = (
                event
                if key == "event_type"
                else impact
                if key == "event_state" or key.startswith("impact_state_")
                else "e1"
                if key.startswith("evidence_")
                else "unknown"
                if key.startswith("duration_")
                else "7"
            )
            probabilities = {k: 1.0 if k == choice else 0.0 for k in keys}
            out[key] = {
                "type": kind,
                "confidence": confidence,
                "probabilities": probabilities,
            }
            if kind == "choice":
                out[key]["choice"] = choice
            else:
                out[key].update(
                    score=7.0, legend={str(i): v for i, v in enumerate(criteria)}
                )
    return {
        "model": payload["model"],
        "answers": out,
        "usage": {"input_tokens": 123, "output_tokens": 45},
    }
