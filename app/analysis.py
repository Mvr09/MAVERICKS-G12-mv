import json, time
from sqlalchemy import select
from jsonschema import validate
from app.db import Session
from app.models import Article, Analysis, Supplier, Batch, now
from app.settings import ROOT, POLICY, settings
from app.duration import durations, VERSION as DURATION_VERSION
from app.profiles import DEFAULT_PROFILE, EXERCISE_PROFILES, CANDIDATE_PROFILE
from app.importer import digest
from app.schemas import NormalizedAnalysis
from app.jev import JevClient, ProviderError
from reference.jev_requests import stage_a, stage_b, sentences
from reference.scoring import priority, decisions

SCHEMA = json.loads((ROOT / "contracts/article_analysis.schema.json").read_text())



def normalize(article, suppliers, a, b, candidates):
    rss = article.context == "rss"
    from app import rss_questions

    notes = []
    threshold = POLICY["thresholds"]
    aa = a["answers"]
    bb = b["answers"] if b else {}
    evidence = rss_questions.sentences(article.data) if rss else sentences(article.data)
    reasons = []
    assessments = []
    for k in ("event_type", "event_state"):
        if aa[k]["confidence"] < threshold["choice_score_confidence"]:
            (notes if rss else reasons).append(k + "_confidence_low")
    if rss:
        metadata = article.data.get("enrichment", {})
        if metadata.get("status") != "public_text":
            notes.append("source_text_limited")
            if "..." in article.data.get("summary", "") or "…" in article.data.get(
                "summary", ""
            ):
                reasons.append("source_text_incomplete")
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
        risk_relevant = not rss or pr >= threshold["review_low"]
        for prefix in ("severity", "impact_state", "evidence", "duration"):
            if get(prefix)["confidence"] < threshold["choice_score_confidence"]:
                (review if risk_relevant else notes).append(prefix + "_confidence_low")
        ev = get("evidence")["choice"]
        duration_id = get("duration")["choice"]
        d = next((x for x in candidates if x["id"] == duration_id), None)
        if ev == "none":
            (review if risk_relevant else notes).append("evidence_missing")
        risk = pl >= threshold["link"] and pr >= threshold["risk"]
        if (
            rss
            and risk
            and aa.get("operational_event", {}).get("noul", 1) < threshold["review_low"]
        ):
            review.append("risk_without_operational_evidence")
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
        review.extend(
            score["warnings"]
        )  # Las invariantes de inventario y catálogo permanecen.
        dec = decisions(
            p_link=pl,
            p_risk=pr,
            p_urgent=pu,
            impact_status=impact if risk_relevant else "unrelated",
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
    if rss:
        for assessment in assessments:
            sid = assessment["supplier_id"]
            assessment["p_identity"] = aa["identity_" + sid]["noul"]
            assessment["p_exposure"] = aa["exposure_" + sid]["noul"]
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
        "event_type": rss_questions.canonical_event(aa["event_type"]["choice"])
        if rss
        else aa["event_type"]["choice"],
        "evidence": evidence,
        "review_reasons": sorted(set(reasons)),
    }
    if rss:
        result["question_version"] = rss_questions.VERSION
        result["context_notes"] = sorted(set(notes))
        category = aa["event_type"]["choice"]
        result["event_classification"] = {
            "category": category,
            "confidence": aa["event_type"]["confidence"],
            "taxonomy_version": rss_questions.TAXONOMY_VERSION,
        }
        if category in rss_questions.EVENT_LABELS:
            result["event_classification"]["label_es"] = rss_questions.EVENT_LABELS[
                category
            ]
        result["source_reading"] = {
            k: v
            for k, v in article.data.get(
                "enrichment", {"status": "summary_only"}
            ).items()
            if k
            in {
                "status",
                "checked_at",
                "source_url",
                "text_hash",
                "characters",
                "http_status",
                "reason",
                "method",
            }
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


def process_article(
    db, article_id, transport=None, diagnostic_ack_at=None, run_key=None, publish=True, profile=DEFAULT_PROFILE
):
    a = db.get(Article, article_id)
    suppliers = [s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
    if len(suppliers) != 40:
        raise ProviderError("CATALOG_REQUIRES_40_SUPPLIERS")
    start = time.monotonic()
    run_key = (
        run_key
        if run_key is not None
        else (f"{a.id}:generation:{a.generation}" if a.generation else "")
    )
    from app.payload_cache import PayloadCacheClient
    candidate = profile == CANDIDATE_PROFILE
    client_type = PayloadCacheClient if candidate else JevClient
    client_options = {}
    if candidate:
        from app.jev_transport import CONFIG as TRANSPORT_CONFIG
        client_options["request_ceiling"] = TRANSPORT_CONFIG["max_http_attempts_per_article"]
    client = client_type(
        db,
        a.id,
        transport=transport,
        diagnostic_ack_at=diagnostic_ack_at,
        run_key=run_key,
        **client_options,
    )
    if candidate:
        from app.jev_audit import CapturingClient
        from app.jev_transport import BoundedFanoutClient
        client = BoundedFanoutClient(CapturingClient(client))
    raw = {}
    rss = a.context == "rss"
    if rss:
        from app.enrichment import enrich
        from app import rss_questions

        enrich(db, a)
        db.commit()
        raw["_reading_snapshot"] = {
            "headline": a.data.get("headline"),
            "summary": a.data.get("summary"),
            "full_text": a.data.get("full_text", ""),
            "enrichment": a.data.get("enrichment", {}),
        }
    from app import link_questions, stable_geography
    geographic = not rss and profile == stable_geography.VERSION
    modern = not rss and profile == link_questions.VERSION
    if profile not in EXERCISE_PROFILES:
        raise ProviderError("UNKNOWN_ANALYSIS_PROFILE")
    if modern or geographic:
        raw["_profile"] = profile
        from app.geography import location
        raw["_geography_snapshot"] = {s["supplier_id"]: location(s) for s in suppliers}
    from app import candidate_engine, candidate_matching
    build_a = rss_questions.stage_a if rss else link_questions.stage_a if modern else stable_geography.stage_a if geographic else stage_a
    build_b = rss_questions.stage_b if rss else link_questions.stage_b if modern else stable_geography.stage_b if geographic else stage_b
    question_version = rss_questions.VERSION if rss else link_questions.VERSION if modern else stable_geography.VERSION if geographic else POLICY["question_version"]
    if candidate:
        question_version = candidate_matching.VERSION
    deadline = time.monotonic() + 60
    pa = candidate_matching.stage_a(a.data, suppliers, settings.jev_model, a.context) if candidate else build_a(a.data, suppliers, settings.jev_model)
    request_hash = digest(
        {
            "article": a.id,
            "payload": pa,
            "policy": POLICY["version"],
            "questions": question_version,
            "duration_parser": DURATION_VERSION,
        }
    )
    if candidate:
        from app.profiles import candidate_versions
        request_hash = digest({"request": request_hash, "versions": candidate_versions()})
    if run_key:
        request_hash = digest({"request": request_hash, "run_key": run_key})
    previous = (
        db.scalar(select(Analysis).where(Analysis.request_hash == request_hash))
        if publish
        else None
    )
    if previous and previous.result["analysis_status"] != "error":
        a.state = previous.result["analysis_status"]
        previous.cached = True
        db.commit()
        return previous.result
    try:
        if candidate:
            result, candidate_raw = candidate_engine.run(client, a, suppliers, deadline)
            raw.update(candidate_raw)
            from app.jev_transport import VERSION as transport_version
            result["analysis_versions"] = {**candidate_engine.VERSIONS, **result.get("analysis_versions", {}), "transport": transport_version, "model": result["model_id"]}
            raw["_versions"] = {**candidate_engine.VERSIONS, **raw.get("_versions", {}), "transport": transport_version}
            validate(result, SCHEMA)
        else:
            raw["a"] = client.ask(pa, "a", deadline)
            if rss:
                rss_questions.linked_answers(raw["a"], suppliers)
            candidates = link_questions.select_candidates(a.data, suppliers, raw["a"]) if modern else [
                s
                for s in suppliers
                if raw["a"]["answers"]["linked_" + s["supplier_id"]]["noul"]
                >= POLICY["thresholds"]["review_low"]
            ]
            duration_candidates = (
                durations(
                    {
                        **a.data,
                        "summary": a.data.get("summary", "")
                        + " "
                        + a.data.get("full_text", ""),
                    }
                )
                if rss
                else durations(a.data)
            )
            raw["b"] = (
                client.ask(
                    build_b(a.data, candidates, duration_candidates, settings.jev_model),
                    "b",
                    deadline,
                )
                if candidates
                else None
            )
            if modern:
                from app.link_analysis import normalize as normalize_link
                result = normalize_link(a, suppliers, raw["a"], raw["b"], duration_candidates)
                NormalizedAnalysis.model_validate(result)
                validate(result, SCHEMA)
            else:
                result = normalize(a, suppliers, raw["a"], raw["b"], duration_candidates)
                if geographic:
                    stable_geography.annotate(result, a, suppliers)
                    NormalizedAnalysis.model_validate(result)
                    validate(result, SCHEMA)
        from app.incidents import reconcile

        result.setdefault("analysis_profile", profile)
        result.setdefault("matching_version", question_version)
        result.setdefault("analysis_versions", {
            "profile": profile, "matching": question_version, "questions": question_version,
            "review": "link-review-2.2.0" if modern else "legacy-review-1.0.0",
            "duration": DURATION_VERSION, "policy": POLICY["version"], "model": result["model_id"],
        })
        if publish:
            if a.generation:
                # A failed replacement rolls back its projection, not prior evidence.
                with db.begin_nested():
                    from app.reanalysis import retire_effects
                    retire_effects(db, a, result)
                    reconcile(db, a, result)
            else:
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
            "question_version": question_version,
            "policy_version": POLICY["version"],
            "error": code,
            "event_type": None,
            "evidence": [],
            "review_reasons": [],
        }
        validate(result, SCHEMA)
    result.setdefault("analysis_profile", profile)
    if candidate:
        from app.profiles import candidate_versions
        result.setdefault("analysis_versions", {**candidate_versions(), "model": settings.jev_model})
    if not publish:
        return result
    if candidate:
        from app.profiles import candidate_versions
        raw.setdefault("_versions", candidate_versions())
        raw.update(client.audit())
        raw["_transport"] = client.transport_records
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
                generation=a.generation,
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
