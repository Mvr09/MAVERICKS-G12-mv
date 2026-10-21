"""Display scope of model review. Stored analyses, export and metrics never change.

A model doubt on a news item with no risk, no urgency, no affected supplier and
no supplier-specific question cannot change a procurement decision. The app
shows it as resolved with a note that keeps the original reasons, instead of
counting it as pending work. If the text names a supplier's city, region or
company, the item stays in review: that is where a missed exposure would hide.
"""
from copy import deepcopy
from sqlalchemy import select
from app.geography import retrieval_hints
from app.models import Supplier

VERSION = "review-scope-1.0.0"
PLACE_HINTS = {"city", "region", "name"}
RULE = ("Sin riesgo, sin urgencia, sin proveedor afectado y sin dudas sobre un "
    "proveedor concreto; el texto no menciona ciudad, región ni nombre de la cartera.")


def catalog(db):
    return [s.data for s in db.scalars(select(Supplier)).all()]


def applies(article_data, result, suppliers, human_state=None):
    if not result or result.get("analysis_status") != "review":
        return False
    # Human work already started on the article is never hidden.
    if human_state not in (None, "pending", "not_required"):
        return False
    if result.get("is_risk") != "N" or result.get("urgent") != "N" or result.get("affected_supplier_ids"):
        return False
    if any(":" in r for r in result.get("review_reasons", [])):
        return False
    if any(a.get("needs_review") for a in result.get("assessments", [])):
        return False
    if any(d.get("supplier_id") and d.get("requires_review") for d in result.get("review_details", [])):
        return False
    return not any(h["kind"] in PLACE_HINTS for s in suppliers for h in retrieval_hints(article_data, s))


def note(result):
    return {"version": VERSION, "model_status": "review",
        "reasons": sorted(result.get("review_reasons", [])), "rule": RULE}


def adjust_article(item, article_data, suppliers):
    """Article view as shown in the app; the stored analysis keeps status and reasons."""
    result = item.get("analysis")
    human = item.get("human_review") or {}
    if item.get("state") != "review" or not applies(article_data, result, suppliers, human.get("state")):
        return item
    scope = note(result)
    shown = deepcopy(result)
    shown["analysis_status"] = "done"
    shown["review_reasons"] = []
    shown["review_details"] = [{**d, "requires_review": False} for d in shown.get("review_details", [])]
    shown["context_notes"] = sorted(set(shown.get("context_notes", []) + scope["reasons"]))
    adjusted = {**item, "state": "done", "analysis": shown, "review_scope": scope}
    if human.get("state") == "pending":
        adjusted["human_review"] = {**human, "state": "not_required", "general_pending": False}
    return adjusted


def adjust_review(record, article_data, result, suppliers):
    """Presenter review panel, consistent with the article view."""
    if not applies(article_data, result, suppliers, record.get("state")):
        return record
    return {**record, "state": "not_required" if record.get("state") == "pending" else record["state"],
        "general_pending": False, "review_scope": note(result)}
