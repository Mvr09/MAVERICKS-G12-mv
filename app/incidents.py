"""Conservative event reconciliation. Ambiguity becomes review, never a guessed closure."""

import re
from datetime import datetime
from sqlalchemy import select
from app.models import Incident, Alert, Supplier, now
from app.importer import digest
from app.event_tags import event_tag
from app.settings import POLICY
from reference.scoring import decisions

EVENT_WORDS = {
    "fire_incident": r"fire|explosion|incendio",
    "natural_disaster": r"flood|earthquake|storm|inundaci|terremoto",
    "labour_strike": r"strike|labour|huelga",
    "regulatory_action": r"regulat|licen[cs]e|inspection|certificat",
    "export_restriction": r"export|trade ban",
    "financial_distress": r"insolven|debt|bankrupt|payment",
    "quality_recall": r"recall|contamin|quality",
    "logistics_disruption": r"port|shipping|logistic|transport",
    "utility_outage": r"power|electric|water|utility",
}
STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "after",
    "supplier",
    "supply",
    "news",
    "plant",
    "helixa",
}


def tokens(text, supplier):
    excluded = set(re.findall(r"\w+", supplier["name"].lower())) | STOP
    return {
        x
        for x in re.findall(r"[\w]+", text.lower())
        if len(x) > 3 and x not in excluded
    }


def similarity(a, b):
    return len(a & b) / max(1, len(a | b))


def daydiff(a, b):
    return abs(
        (
            datetime.fromisoformat(a.replace("Z", "+00:00")).date()
            - datetime.fromisoformat(b.replace("Z", "+00:00")).date()
        ).days
    )


def reconcile(db, article, result):
    # Serialize supplier/context histories even when multiple jobs finish simultaneously.
    for assessment in sorted(result["assessments"], key=lambda a: a["supplier_id"]):
        if assessment["p_link"] < POLICY["thresholds"]["link"]:
            continue
        supplier = db.scalar(
            select(Supplier)
            .where(Supplier.id == assessment["supplier_id"])
            .with_for_update()
        )
        s = supplier.data
        published = article.data["published_date"]
        event = result["event_type"]
        text = article.data["headline"] + " " + article.data["summary"]
        words = tokens(text, s)
        incidents = db.scalars(
            select(Incident)
            .where(
                Incident.supplier_id == supplier.id, Incident.context == article.context
            )
            .with_for_update()
        ).all()
        selected_evidence = [
            e["text"]
            for e in result["evidence"]
            if e["id"] in assessment["evidence_ids"]
        ]
        explanation = f"{s['name']}: " + (
            " ".join(selected_evidence)
            if selected_evidence
            else "Sin fragmento suficiente para una conclusión fiable."
        )
        entry = {
            "article_id": article.id,
            "event_tag": event_tag(result),
            "origin_key": article.origin_key,
            "headline": article.data["headline"],
            "published_date": published,
            "at": now().isoformat(),
            "assessment": assessment,
            "explanation": explanation,
            "tokens": sorted(words),
        }
        recovery = assessment["impact_status"] == "resolved" or event == "recovery"
        if recovery:
            compatible = [
                i
                for i in incidents
                if i.event_type in EVENT_WORDS
                and re.search(EVENT_WORDS[i.event_type], text, re.I)
                and published > i.event_date
            ]
            active = [i for i in compatible if i.state != "resolved"]
            if len(active) == 1 and not assessment["needs_review"]:
                inc = active[0]
                inc.state = "resolved"
                inc.priority = 0
                inc.event_date = published
                inc.revision += 1
                inc.history = [*inc.history, entry]
                for alert in db.scalars(
                    select(Alert).where(Alert.incident_id == inc.id)
                ):
                    alert.data = {
                        **alert.data,
                        "state": "resolved",
                        "sound_eligible": False,
                    }
            else:
                result["review_reasons"] = sorted(
                    set(
                        result["review_reasons"]
                        + ["recovery_requires_compatible_incident"]
                    )
                )
                result["analysis_status"] = "review"
                assessment["needs_review"] = True
                assessment["review_reasons"] = sorted(
                    set(
                        assessment["review_reasons"]
                        + ["recovery_requires_compatible_incident"]
                    )
                )
            continue
        if assessment["is_risk"] != "Y" or assessment["priority"] is None:
            continue
        compatible = [
            i
            for i in incidents
            if i.event_type == event
            and (
                any(
                    (
                        h.get("article_id") == article.id
                        or h.get("origin_key") == article.origin_key
                    )
                    for h in i.history
                )
                or (
                    daydiff(i.event_date, published) <= 7
                    and any(
                        similarity(words, set(h.get("tokens", []))) >= 0.5
                        for h in i.history
                        if h.get("assessment", {}).get("is_risk") == "Y"
                    )
                )
            )
        ]
        if len(compatible) > 1:
            result["analysis_status"] = "review"
            result["review_reasons"] = sorted(
                set(result["review_reasons"] + ["event_group_ambiguous"])
            )
            continue
        inc = compatible[0] if compatible else None
        if inc:
            # Retain late evidence but never reopen or replace a more recent state.
            if any(h.get("article_id") == article.id for h in inc.history):
                continue
            if published <= inc.event_date:
                inc.history = [*inc.history, entry]
                continue
            inc.history = [*inc.history, entry]
            if inc.state == "resolved":
                result["analysis_status"] = "review"
                result["review_reasons"] = sorted(
                    set(result["review_reasons"] + ["resolved_event_requires_review"])
                )
                continue
            inc.state = (
                assessment["impact_status"]
                if assessment["impact_status"] in ("active", "monitoring")
                else "monitoring"
            )
            changed = (
                inc.priority != assessment["priority"]
                or inc.history[-2]["assessment"]["urgent"] != assessment["urgent"]
            )
            inc.priority = assessment["priority"]
            inc.historical_priority = max(inc.historical_priority, inc.priority)
            inc.event_date = published
            if not changed:
                continue
            inc.revision += 1
        else:
            inc = Incident(
                context=article.context,
                supplier_id=supplier.id,
                event_type=event,
                signature=digest([supplier.id, event, sorted(words)]),
                state=assessment["impact_status"]
                if assessment["impact_status"] in ("active", "monitoring")
                else "monitoring",
                priority=assessment["priority"],
                historical_priority=assessment["priority"],
                event_date=published,
                history=[entry],
            )
            db.add(inc)
            db.flush()
        if (
            assessment["urgent"] == "Y"
            or assessment["priority_band"] == "critical"
            or assessment["needs_review"]
        ):
            gate = decisions(
                p_link=assessment["p_link"],
                p_risk=assessment["p_risk"],
                p_urgent=assessment["p_urgent"],
                impact_status=inc.state,
                needs_review=assessment["needs_review"],
            )
            db.add(
                Alert(
                    incident_id=inc.id,
                    revision=inc.revision,
                    data={
                        "supplier_id": supplier.id,
                        "supplier_name": s["name"],
                        "priority": inc.priority,
                        "headline": article.data["headline"],
                        "event_tag": event_tag(result),
                        "needs_review": assessment["needs_review"],
                        "urgent": assessment["urgent"],
                        "human_attention": assessment.get("human_attention"),
                        "priority_requires_review": assessment.get("priority_requires_review", False),
                        "review_policy_version": assessment.get("review_policy_version"),
                        "sound_eligible": gate["sound_eligible"],
                        "state": inc.state,
                        "article_id": article.id,
                        "origin_key": article.origin_key,
                    },
                )
            )
