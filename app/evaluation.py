from sqlalchemy import select
from app.models import Batch, Article, EvaluationLabel, Analysis


def evaluate_batch(db, bid):
    batch = db.get(Batch, bid)
    if not batch or batch.split not in ("training", "validation"):
        raise ValueError("Solo entrenamiento y validación con etiquetas disponibles")
    pairs = []
    for a in db.scalars(select(Article).where(Article.batch_id == bid)):
        label = db.get(EvaluationLabel, a.id)
        analysis = db.scalar(
            select(Analysis)
            .where(Analysis.article_id == a.id, Analysis.generation == a.generation)
            .order_by(Analysis.created_at.desc())
        )
        if (
            not label
            or not analysis
            or a.state not in ("done", "review")
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

    def metric(field, out):
        tp = fp = fn = tn = 0
        for l, r in pairs:
            y = l[field] == "Y"
            p = r[out] == "Y"
            tp += y and p
            fp += not y and p
            fn += y and not p
            tn += not y and not p
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        return dict(
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            precision=precision,
            recall=recall,
            f1=2 * precision * recall / (precision + recall)
            if precision + recall
            else 0,
            n=len(pairs),
        )

    exact = tp = fp = fn = 0
    for l, r in pairs:
        expected = {
            s.strip()
            for s in str(l.get("Affected_Supplier_IDs", ""))
            .replace(",", ";")
            .split(";")
            if s.strip()
        }
        actual = set(r["affected_supplier_ids"])
        exact += actual == expected
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)
    return {
        "split": batch.split,
        "n": len(pairs),
        "risk": metric("Is_Risk", "is_risk"),
        "urgent": metric("Urgent", "urgent"),
        "suppliers": {
            "exact": exact,
            "n": len(pairs),
            "precision": tp / (tp + fp) if tp + fp else 0,
            "recall": tp / (tp + fn) if tp + fn else 0,
            "exact_set_accuracy": exact / len(pairs),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
        },
        "review_count": sum(r["analysis_status"] == "review" for _, r in pairs),
        "question_version": pairs[0][1]["question_version"] if pairs else None,
    }
