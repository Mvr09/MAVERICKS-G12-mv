"""Private, read-only attribution of stored exercise results. Never used for inference."""
from collections import Counter
from sqlalchemy import select
from app.models import Article, Analysis, Batch, EvaluationLabel, now
from app.evaluation import evaluate_batch
from app.settings import POLICY
from app.views import batch_label


def supplier_ids(value):
    return sorted({s.strip() for s in str(value or "").replace(",", ";").split(";") if s.strip()})


def review_trace(result, raw):
    """Trace the actual normalizer's review gates, including inherited reasons.

    Scope is diagnostic relevance, not permission to remove a review. Discarded
    identity candidates may still need review; no decisions are recomputed.
    """
    t = POLICY["thresholds"]
    aa = raw.get("a", {}).get("answers", {})
    bb = (raw.get("b") or {}).get("answers", {})
    trace = []
    inherited = []
    decision_gates = []
    for reason in result["review_reasons"]:
        code, _, sid = reason.partition(":")
        if code == "link_ambiguous":
            p = aa.get("linked_" + sid, {}).get("noul")
            scope = "discarded_candidate" if p is not None and p < t["link"] else "decision"
            detail = {"p_link": p, "review_interval": [t["review_low"], t["review_high"]], "accept_threshold": t["link"]}
        elif code in {"event_type_confidence_low", "event_state_confidence_low"}:
            field = code.removesuffix("_confidence_low")
            scope = "auxiliary"
            detail = {"field": field, "confidence": aa.get(field, {}).get("confidence"), "choice": aa.get(field, {}).get("choice"), "threshold": t["choice_score_confidence"]}
        else:
            scope, detail = "unattributed", {"limitation": "Motivo no reconstruido por este diagnóstico."}
        trace.append({"code": reason, "supplier_id": sid or None, "scope": scope, "origin": "article", "details": detail})
    # In the original exercise profile, reasons accumulate in supplier-ID order.
    global_seed = [r for r in trace if r["code"] in {"event_type_confidence_low", "event_state_confidence_low"}]
    for assessment in result["assessments"]:
        sid = assessment["supplier_id"]
        accepted = assessment["p_link"] >= t["link"]
        risk = accepted and assessment["p_risk"] >= t["risk"]
        scope = "discarded_candidate" if not accepted else "decision" if risk else "auxiliary"
        # decisions() can flag a numerical ambiguity even when normalize()
        # stores only an earlier auxiliary reason. Trace those gates as well;
        # they are NOT additional stored reason codes or changed decisions.
        values = [("p_link", assessment["p_link"])]
        if accepted:
            values.append(("p_risk", assessment["p_risk"]))
        if risk:
            values.append(("p_urgent", assessment["p_urgent"]))
        for field, value in values:
            if t["review_low"] <= value <= t["review_high"]:
                decision_gates.append({"supplier_id": sid, "field": field, "value": value,
                    "scope": "discarded_candidate" if not accepted else "decision",
                    "rule": "review_low <= value <= review_high"})
        if assessment["impact_status"] == "unclear" or risk and assessment["impact_status"] in {"resolved", "positive", "unrelated"}:
            decision_gates.append({"supplier_id": sid, "field": "impact_status", "value": assessment["impact_status"], "scope": scope,
                "rule": "unclear or risk/impact contradiction"})
        for code in assessment["review_reasons"]:
            item = {"code": code, "supplier_id": sid, "scope": scope, "origin": "assessment", "details": {}}
            if code == "decision_ambiguous_or_contradictory":
                causes = []
                relevant = [("p_link", assessment["p_link"])]
                if accepted:
                    relevant.append(("p_risk", assessment["p_risk"]))
                if risk:
                    relevant.append(("p_urgent", assessment["p_urgent"]))
                for field, value in relevant:
                    if t["review_low"] <= value <= t["review_high"]:
                        causes.append({"cause": field + "_ambiguous", "value": value, "scope": "discarded_candidate" if not accepted else "decision", "interval": [t["review_low"], t["review_high"]]})
                if assessment["impact_status"] == "unclear":
                    causes.append({"cause": "impact_status_unclear", "value": "unclear", "scope": scope})
                if risk and assessment["impact_status"] in {"resolved", "positive", "unrelated"}:
                    causes.append({"cause": "risk_impact_contradiction", "value": assessment["impact_status"], "scope": "decision"})
                propagated = global_seed + [r for r in trace if r["origin"] == "article" and r["code"].startswith("link_ambiguous:") and r["supplier_id"] <= sid]
                item["details"] = {"direct_causes": causes, "inherited_from": [r["code"] for r in propagated]}
                item["scope"] = "inherited" if propagated and not causes else "unattributed" if not causes else causes[0]["scope"]
                if propagated:
                    inherited.append({"supplier_id": sid, "from": item["details"]["inherited_from"]})
                # Root scopes below use every direct cause, not merely the first.
                item["root_scopes"] = sorted({c["scope"] for c in causes})
            elif code.endswith("_confidence_low"):
                field = code.removesuffix("_confidence_low")
                observed = bb.get(field + "_" + sid, {})
                item["details"] = {"field": field, "confidence": observed.get("confidence"), "choice": observed.get("choice"), "score": observed.get("score"), "threshold": t["choice_score_confidence"]}
            elif code == "evidence_missing":
                item["details"] = {"evidence_choice": bb.get("evidence_" + sid, {}).get("choice")}
            elif code in {"inventory_missing", "buffer_horizon_missing", "criticality_missing", "single_source_missing", "category_share_missing", "severity_missing", "critical_without_urgency"}:
                item["details"] = {"priority": assessment["priority"], "is_risk": assessment["is_risk"], "factor_values": assessment["factor_values"], "duration_days": assessment.get("duration_days")}
            else:
                item["scope"] = "unattributed"
            trace.append(item)
    roots = set()
    for item in trace:
        roots.update(item.get("root_scopes", [item["scope"]]))
    roots.update(g["scope"] for g in decision_gates)
    roots.discard("inherited")
    return {"causes": trace, "decision_gates": decision_gates, "root_scopes": sorted(roots), "inherited": inherited,
            "raw_available": bool(aa), "status_explained": result["analysis_status"] != "review" or bool(trace)}


def diagnose_batch(db, bid):
    metrics = evaluate_batch(db, bid)  # Same completeness/labels/version gates.
    batch = db.get(Batch, bid)
    rows = []
    t = POLICY["thresholds"]
    if metrics["policy_version"] != POLICY["version"]:
        raise ValueError("Política histórica no disponible: no atribuir con umbrales distintos")
    for article in db.scalars(select(Article).where(Article.batch_id == bid).order_by(Article.row_order)):
        label = db.get(EvaluationLabel, article.id).data
        run = db.scalar(select(Analysis).where(Analysis.article_id == article.id, Analysis.generation == article.generation).order_by(Analysis.created_at.desc()))
        result = run.result
        expected = supplier_ids(label.get("Affected_Supplier_IDs"))
        actual = result["affected_supplier_ids"]
        aa = run.raw.get("a", {}).get("answers", {})
        assessments = {a["supplier_id"]: a for a in result["assessments"]}
        supplier_gates = []
        for sid in sorted(set(expected) | set(actual)):
            p = aa.get("linked_" + sid, {}).get("noul")
            assessment = assessments.get(sid)
            supplier_gates.append({"supplier_id": sid, "expected": sid in expected, "predicted": sid in actual,
                "p_link": p, "stage_b_evaluated": bool(assessment),
                "p_risk": assessment["p_risk"] if assessment else None,
                "p_urgent": assessment["p_urgent"] if assessment else None,
                "gate": "raw_unavailable" if p is None else "excluded_before_stage_b" if p < t["review_low"] else "below_link_threshold" if p < t["link"] else "below_risk_threshold" if assessment and assessment["p_risk"] < t["risk"] else "risk_accepted" if assessment else "assessment_unavailable"})
        rows.append({"article_id": article.id, "news_id": article.news_id, "headline": article.data["headline"], "summary": article.data["summary"], "row_order": article.row_order,
            "reference": {"is_risk": label["Is_Risk"], "urgent": label["Urgent"], "affected_supplier_ids": expected, "explanation": label.get("Explanation"), "event_type": label.get("Event_Type")},
            "prediction": {k: result[k] for k in ("is_risk", "urgent", "affected_supplier_ids", "analysis_status", "review_reasons")},
            "risk_false_negative": label["Is_Risk"] == "Y" and result["is_risk"] == "N",
            "missing_suppliers": sorted(set(expected) - set(actual)), "extra_suppliers": sorted(set(actual) - set(expected)),
            "supplier_gates": supplier_gates, "review": review_trace(result, run.raw), "generation": run.generation,
            "analysis_created_at": run.created_at})
    reviewed = [r for r in rows if r["prediction"]["analysis_status"] == "review"]
    return {"batch_id": bid, "filename": batch_label(batch), "split": batch.split, "created_at": now(),
        "thresholds": t, "metrics": metrics, "rows": rows,
        "summary": {"risk_false_negatives": sum(r["risk_false_negative"] for r in rows), "missing_supplier_associations": sum(len(r["missing_suppliers"]) for r in rows),
            "reviewed_news": len(reviewed), "review_scope_combinations": dict(Counter(" + ".join(r["review"]["root_scopes"]) or "unattributed" for r in reviewed))},
        "limitations": ["Diagnóstico de resultados almacenados: no ejecuta inferencia ni modifica umbrales.",
            "Validación ya inspeccionada: cualquier corrección debe desarrollarse con training; una repetición de este lote no es una nueva evaluación independiente.",
            "Las probabilidades explican dónde se pierde una decisión, no la causa psicológica del modelo.",
            "Candidato descartado o campo auxiliar no implica que sea seguro eliminar su revisión."]}
