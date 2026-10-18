"""Version 2 association and field-specific review; policy thresholds unchanged."""
from app.settings import POLICY
from reference.scoring import priority
from app.geography import location
from app.link_questions import VERSION
from reference.jev_requests import sentences


def normalize(article, suppliers, a, b, durations):
    t = POLICY["thresholds"]
    aa, bb = a["answers"], (b or {}).get("answers", {})
    details, assessments = [], []
    def note(code, field, sid, relevant, value=None, threshold=None):
        details.append({"code": code, "field": field, "supplier_id": sid,
            "relevance": relevant, "requires_review": relevant != "auxiliary",
            "value": value, "threshold": threshold})
    for field in ("event_type", "event_state"):
        if aa[field]["confidence"] < t["choice_score_confidence"]:
            note(field + "_confidence_low", field, None, "auxiliary", aa[field]["confidence"], t["choice_score_confidence"])
    if not bb and aa["article_threat"]["noul"] >= t["review_low"]:
        note("scope_coverage_unconfirmed", "article_threat_without_candidates", None, "association", aa["article_threat"]["noul"], t["review_low"])
    for s in suppliers:
        sid = s["supplier_id"]
        if "identity_" + sid not in bb:
            continue
        get = lambda p: bb[p + "_" + sid]
        pi = get("identity")["noul"]
        pe = min(get("area")["noul"], get("operation")["noul"])
        pl = max(pi, pe)  # Independent final B answers, never conditional risk or A.
        pr, pu = get("risk")["noul"], get("urgent")["noul"]
        linked = pl >= t["link"]
        risk = linked and pr >= t["risk"]
        urgent = risk and pu >= t["urgent"]
        first = len(details)
        ev, impact = get("evidence"), get("impact_state")
        lev = get("link_evidence")
        association_reliable = get("association_support")["noul"] > t["review_high"] and lev["choice"] != "none"
        if t["review_low"] <= pl <= t["review_high"]:
            note("link_ambiguous", "final_link", sid, "association", pl, t["link"])
        if not association_reliable:
            note("association_support_insufficient", "scope_and_link_evidence", sid, "association", get("association_support")["noul"], t["review_high"])
        geo = location(s)
        if geo["status"] != "matched":
            # Explicit identity can establish the entity despite unknown site.
            if pe >= t["link"] and pi < t["link"] and (geo["status"] == "unresolved" or len({p.get("admin1", {}).get("geoname_id") for p in geo["places"] if p.get("admin1")}) > 1):
                note("geography_requires_review", "geography", sid, "association", geo["status"])
            else:
                note("geography_not_resolved", "geography", sid, "auxiliary", geo["status"])
        if linked:
            if t["review_low"] <= pr <= t["review_high"]:
                note("risk_ambiguous", "risk", sid, "risk", pr, t["risk"])
            if ev["choice"] == "none" or get("risk_support")["noul"] <= t["review_high"]:
                note("risk_evidence_insufficient", "risk_evidence", sid, "risk", get("risk_support")["noul"], t["review_high"])
            if risk and t["review_low"] <= pu <= t["review_high"]:
                note("urgency_ambiguous", "urgent", sid, "urgency", pu, t["urgent"])
            if risk and impact["choice"] in ("resolved", "positive", "unrelated", "unclear"):
                note("risk_impact_contradiction", "impact_state", sid, "risk", impact["choice"])
        # Choice can be diffuse among several valid literal passages. Its
        # uncertainty is still shown; support has a separate independent Noul.
        for prefix in ("link_evidence", "evidence"):
            if get(prefix)["confidence"] < t["choice_score_confidence"]:
                note(prefix + "_confidence_low", prefix, sid, "auxiliary", get(prefix)["confidence"], t["choice_score_confidence"])
        for prefix in ("severity", "impact_state", "duration"):
            if get(prefix)["confidence"] < t["choice_score_confidence"]:
                relevance = "priority" if risk and prefix in ("severity", "duration") else "risk" if risk else "auxiliary"
                note(prefix + "_confidence_low", prefix, sid, relevance, get(prefix)["confidence"], t["choice_score_confidence"])
        duration = next((d for d in durations if d["id"] == get("duration")["choice"]), None)
        severity = 1 + get("severity")["score"]
        score = priority(is_risk=risk, severity=severity, criticality=s["criticality"], single_source=s["single_source"],
            share_category_pct=s["share_category_pct"], inventory_days=s["inventory_days"], lead_days=s["lead_days"],
            disruption_days=duration["days"] if duration else None,
            inventory_applicability="not_applicable" if s["category"] in POLICY["buffer_not_applicable_categories"] else "physical")
        for warning in score["warnings"]:
            # Data invariants still require review for an associated risk.
            note(warning, "catalog_or_buffer", sid, "priority" if risk else "auxiliary")
        if risk and score["band"] == "critical" and not urgent:
            note("critical_without_urgency", "priority", sid, "priority", score["priority"])
        own = details[first:]
        association_review = any(d["requires_review"] and d["relevance"] == "association" for d in own)
        evidence_ids = sorted({x["choice"] for x in (lev, ev) if x["choice"] != "none"})
        assessments.append({"supplier_id": sid, "p_link": pl, "p_identity": pi, "p_exposure": pe,
            "p_candidate": aa["candidate_" + sid]["noul"],
            "association_status": "review" if association_review else "confirmed" if linked else "excluded",
            "geography_version": geo["version"], "p_risk": pr, "p_urgent": pu,
            "is_risk": "Y" if risk else "N", "urgent": "Y" if urgent else "N",
            "severity": severity, "severity_confidence": get("severity")["confidence"],
            "priority": score["priority"], "priority_band": score["band"], "impact_status": impact["choice"],
            "needs_review": any(d["requires_review"] for d in own),
            "review_reasons": sorted({d["code"] for d in own if d["requires_review"]}),
            "evidence_ids": evidence_ids, "duration_days": duration["days"] if duration else None,
            "duration_is_lower_bound": duration["lower_bound"] if duration else False,
            "factor_values": score["factors"], "policy_version": POLICY["version"]})
    accepted = [s for s in assessments if s["p_link"] >= t["link"]]
    reasons = sorted({d["code"] + (":" + d["supplier_id"] if d["supplier_id"] else "") for d in details if d["requires_review"]})
    notes = sorted({d["code"] + (":" + d["supplier_id"] if d["supplier_id"] else "") for d in details if not d["requires_review"]})
    return {"article_id": article.id, "news_id": article.news_id, "context_id": article.context,
        "analysis_status": "review" if reasons else "done", "is_risk": "Y" if any(s["is_risk"] == "Y" for s in accepted) else "N",
        "urgent": "Y" if any(s["urgent"] == "Y" for s in accepted) else "N",
        "affected_supplier_ids": sorted(s["supplier_id"] for s in accepted), "assessments": assessments,
        "model_id": a["model"], "question_version": VERSION, "policy_version": POLICY["version"], "error": None,
        "event_type": aa["event_type"]["choice"], "evidence": sentences(article.data),
        "review_reasons": reasons, "context_notes": notes, "review_details": details}
