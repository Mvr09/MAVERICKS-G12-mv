"""Evaluación supervisada agregada. Nunca expone etiquetas ni inicia inferencias."""

from sqlalchemy import select
from app.models import Batch, Article, EvaluationLabel, Analysis


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def metrics(pairs):
    def binary(field, out):
        tp = fp = fn = tn = 0
        for label, result in pairs:
            y, p = label[field] == "Y", result[out] == "Y"
            tp += y and p
            fp += not y and p
            fn += y and not p
            tn += not y and not p
        return dict(
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            precision=ratio(tp, tp + fp),
            recall=ratio(tp, tp + fn),
            f1=ratio(2 * tp, 2 * tp + fp + fn),
            n=len(pairs),
            positives=tp + fn,
        )

    exact = tp = fp = fn = 0
    for label, result in pairs:
        expected = {
            s.strip()
            for s in str(label.get("Affected_Supplier_IDs") or "")
            .replace(",", ";")
            .split(";")
            if s.strip()
        }
        actual = set(result["affected_supplier_ids"])
        exact += actual == expected
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)
    return {
        "n": len(pairs),
        "risk": binary("Is_Risk", "is_risk"),
        "urgent": binary("Urgent", "urgent"),
        "suppliers": dict(
            exact=exact,
            n=len(pairs),
            precision=ratio(tp, tp + fp),
            recall=ratio(tp, tp + fn),
            exact_set_accuracy=ratio(exact, len(pairs)),
            tp=tp,
            fp=fp,
            fn=fn,
            f1=ratio(2 * tp, 2 * tp + fp + fn),
        ),
        "review_count": sum(r["analysis_status"] == "review" for _, r in pairs),
    }


def evaluate_batch(db, bid):
    batch = db.get(Batch, bid)
    if not batch or batch.split not in ("training", "validation"):
        raise ValueError("Sin etiquetas de referencia: no se calcula precisión ni F1")
    pairs = []
    for article in db.scalars(select(Article).where(Article.batch_id == bid)):
        label = db.get(EvaluationLabel, article.id)
        analysis = db.scalar(
            select(Analysis)
            .where(
                Analysis.article_id == article.id,
                Analysis.generation == article.generation,
            )
            .order_by(Analysis.created_at.desc())
        )
        if (
            not label
            or not analysis
            or article.state not in ("done", "review")
            or analysis.result.get("analysis_status") not in ("done", "review")
        ):
            raise ValueError("Evaluación bloqueada: lote incompleto")
        if any(
            label.data.get(field) not in ("Y", "N") for field in ("Is_Risk", "Urgent")
        ):
            raise ValueError(
                "Evaluación bloqueada: etiquetas binarias ausentes o inválidas"
            )
        pairs.append((label.data, analysis.result))
    if not pairs:
        raise ValueError("Evaluación bloqueada: lote vacío")
    versions = {
        (r["model_id"], r["question_version"], r["policy_version"]) for _, r in pairs
    }
    if len(versions) != 1:
        raise ValueError("Evaluación bloqueada: versiones mezcladas en el lote")
    model, questions, policy = next(iter(versions))
    automatic = [pair for pair in pairs if pair[1]["analysis_status"] == "done"]
    reviewed = [pair for pair in pairs if pair[1]["analysis_status"] == "review"]
    return {
        **metrics(pairs),
        "split": batch.split,
        "model_id": model,
        "question_version": questions,
        "policy_version": policy,
        "automatic": metrics(automatic) if automatic else None,
        "under_review": metrics(reviewed) if reviewed else None,
        "review_rate": len(reviewed) / len(pairs),
        "automatic_coverage": len(automatic) / len(pairs),
        "includes_review_predictions": True,
    }
