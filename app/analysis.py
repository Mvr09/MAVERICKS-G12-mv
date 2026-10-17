import json, re, time
from sqlalchemy import select
from jsonschema import validate
from app.db import Session
from app.models import Article, Analysis, Supplier, Batch, now
from app.settings import ROOT, POLICY, settings
from app.importer import digest
from app.schemas import NormalizedAnalysis
from app.jev import JevClient, ProviderError
from reference.jev_requests import stage_a, stage_b, sentences
from reference.scoring import priority, decisions

SCHEMA = json.loads((ROOT / "contracts/article_analysis.schema.json").read_text())


def durations(article):
    text = article.get("headline", "") + " " + article.get("summary", "")
    out = []
    pattern = r"(?:(at least|more than|al menos|más de)\s+)?(\d+(?:\.\d+)?)\s*(days?|weeks?|months?|días?|semanas?|meses?)\b"
    for m in re.finditer(pattern, text, re.I):
        n = float(m[2])
        u = m[3].lower()
        days = n * (
            7
            if u.startswith(("week", "semana"))
            else 30
            if u.startswith(("month", "mes"))
            else 1
        )
        if days > 0:
            out.append(
                {
                    "id": f"d{len(out) + 1}",
                    "text": m[0],
                    "days": days,
                    "lower_bound": bool(m[1]),
                }
            )
    return out


def normalize(article, suppliers, a, b, candidates):
    threshold = POLICY["thresholds"]
    aa = a["answers"]
    bb = b["answers"] if b else {}
    evidence = sentences(article.data)
    reasons = []
    assessments = []
    for k in ("event_type", "event_state"):
        if aa[k]["confidence"] < threshold["choice_score_confidence"]:
            reasons.append(k + "_confidence_low")
    for s in suppliers:
        sid = s["supplier_id"]
        pl = aa["linked_" + sid]["noul"]
        if threshold["review_low"] <= pl <= threshold["review_high"]:
            reasons.append("link_ambiguous:" + sid)
        if pl < threshold["review_low"]:
            continue
        get = lambda prefix: bb[prefix + "_" + sid]
        pr = get("risk")["noul"]
        pu = get("urgent")["noul"]
        severity = 1 + get("severity")["score"]
        impact = get("impact_state")["choice"]
        review = []
        for prefix in ("severity", "impact_state", "evidence", "duration"):
            if get(prefix)["confidence"] < threshold["choice_score_confidence"]:
                review.append(prefix + "_confidence_low")
        ev = get("evidence")["choice"]
        duration_id = get("duration")["choice"]
        d = next((x for x in candidates if x["id"] == duration_id), None)
        if ev == "none":
            review.append("evidence_missing")
        risk = pl >= threshold["link"] and pr >= threshold["risk"]
        score = priority(
            is_risk=risk,
            severity=severity,
            criticality=s["criticality"],
            single_source=s["single_source"],
            share_category_pct=s["share_category_pct"],
            inventory_days=s["inventory_days"],
            lead_days=s["lead_days"],
            disruption_days=d["days"] if d else None,
            inventory_applicability="not_applicable"
            if s["category"] in POLICY["buffer_not_applicable_categories"]
            else "physical",
        )
        review += score["warnings"]
        dec = decisions(
            p_link=pl,
            p_risk=pr,
            p_urgent=pu,
            impact_status=impact,
            needs_review=bool(review or reasons),
        )
        if (
            score["priority"] is not None
            and score["band"] == "critical"
            and dec["urgent"] == "N"
            and risk
        ):
            review.append("critical_without_urgency")
        if dec["needs_review"] and not review:
            review.append("decision_ambiguous_or_contradictory")
        assessments.append(
            {
                "supplier_id": sid,
                "p_link": pl,
                "p_risk": pr,
                "p_urgent": pu,
                "is_risk": dec["is_risk"],
                "urgent": dec["urgent"],
                "severity": severity,
                "severity_confidence": get("severity")["confidence"],
                "priority": score["priority"],
                "priority_band": score["band"],
                "impact_status": impact,
                "needs_review": bool(review or dec["needs_review"]),
                "review_reasons": sorted(set(review)),
                "evidence_ids": [] if ev == "none" else [ev],
                "duration_days": d["days"] if d else None,
                "duration_is_lower_bound": d["lower_bound"] if d else False,
                "factor_values": score["factors"],
                "policy_version": POLICY["version"],
            }
        )
    accepted = [s for s in assessments if s["p_link"] >= threshold["link"]]
    result = {
        "article_id": article.id,
        "news_id": article.news_id,
        "context_id": article.context,
        "analysis_status": "review"
        if reasons or any(s["needs_review"] for s in assessments)
        else "done",
        "is_risk": "Y" if any(s["is_risk"] == "Y" for s in accepted) else "N",
        "urgent": "Y" if any(s["urgent"] == "Y" for s in accepted) else "N",
        "affected_supplier_ids": sorted(s["supplier_id"] for s in accepted),
        "assessments": assessments,
        "model_id": a["model"],
        "question_version": POLICY["question_version"],
        "policy_version": POLICY["version"],
        "error": None,
        "event_type": aa["event_type"]["choice"],
        "evidence": evidence,
        "review_reasons": sorted(set(reasons)),
    }
    NormalizedAnalysis.model_validate(result)
    valid_evidence = {e["id"] for e in result["evidence"]}
    for e in result["evidence"]:
        if article.data[e["field"]][e["start"] : e["end"]] != e["text"]:
            raise ValueError("Evidencia fuera del texto original")
    for assessment in result["assessments"]:
        if not set(assessment["evidence_ids"]).issubset(valid_evidence):
            raise ValueError("Referencia de evidencia inválida")
    validate(result, SCHEMA)
    return result


def process_article(db, article_id, transport=None, diagnostic_ack_at=None):
    a = db.get(Article, article_id)
    suppliers = [s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
    if len(suppliers) != 40:
        raise ProviderError("CATALOG_REQUIRES_40_SUPPLIERS")
    start = time.monotonic()
    client = JevClient(
        db, a.id, transport=transport, diagnostic_ack_at=diagnostic_ack_at
    )
    raw = {}
    pa = stage_a(a.data, suppliers, settings.jev_model)
    request_hash = digest(
        {
            "article": a.id,
            "payload": pa,
            "policy": POLICY["version"],
            "questions": POLICY["question_version"],
        }
    )
    previous = db.scalar(select(Analysis).where(Analysis.request_hash == request_hash))
    if previous and previous.result["analysis_status"] != "error":
        a.state = previous.result["analysis_status"]
        previous.cached = True
        db.commit()
        return previous.result
    try:
        raw["a"] = client.ask(pa, "a", start + 60)
        candidates = [
            s
            for s in suppliers
            if raw["a"]["answers"]["linked_" + s["supplier_id"]]["noul"]
            >= POLICY["thresholds"]["review_low"]
        ]
        duration_candidates = durations(a.data)
        raw["b"] = (
            client.ask(
                stage_b(a.data, candidates, duration_candidates, settings.jev_model),
                "b",
                start + 60,
            )
            if candidates
            else None
        )
        result = normalize(a, suppliers, raw["a"], raw["b"], duration_candidates)
        from app.incidents import reconcile

        reconcile(db, a, result)
    except (ProviderError, ValueError) as exc:
        code = exc.code if isinstance(exc, ProviderError) else "DATA_INVALID"
        result = {
            "article_id": a.id,
            "news_id": a.news_id,
            "context_id": a.context,
            "analysis_status": "error",
            "is_risk": None,
            "urgent": None,
            "affected_supplier_ids": [],
            "assessments": [],
            "model_id": settings.jev_model,
            "question_version": POLICY["question_version"],
            "policy_version": POLICY["version"],
            "error": code,
            "event_type": None,
            "evidence": [],
            "review_reasons": [],
        }
        validate(result, SCHEMA)
    raw["_cache_stages"] = client.cached_stages
    raw["_new_requests"] = client.network_requests
    fully_cached = bool(client.cached_stages) and client.network_requests == 0
    if previous:
        previous.result = result
        previous.raw = raw
        previous.duration = time.monotonic() - start
        previous.cached = fully_cached
    else:
        db.add(
            Analysis(
                article_id=a.id,
                request_hash=request_hash,
                result=result,
                raw=raw,
                duration=time.monotonic() - start,
                cached=fully_cached,
            )
        )
    a.state = result["analysis_status"]
    db.flush()
    if a.batch_id:
        b = db.get(Batch, a.batch_id)
        rows = db.scalars(select(Article).where(Article.batch_id == b.id)).all()
        if all(x.state in ("done", "review") for x in rows):
            b.completed_at = now()
    db.commit()
    return result
