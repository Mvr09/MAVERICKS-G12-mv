from copy import deepcopy
from app import review_scope

TANGIER = {"supplier_id": "S040", "name": "Atlas Cleanroom Garments", "country": "Morocco", "city": "Tangier"}


def result(**extra):
    base = {"analysis_status": "review", "is_risk": "N", "urgent": "N", "affected_supplier_ids": [],
        "review_reasons": ["event_state_confidence_low"], "assessments": [], "review_details": [],
        "context_notes": []}
    return {**base, **extra}


def article(headline="Brazilian real hits two-year high", summary="Currency markets moved."):
    return {"headline": headline, "summary": summary}


def item(res, human=None):
    return {"id": "a1", "state": "review", "analysis": res, "human_review": human}


def test_doubt_without_supplier_or_risk_is_shown_resolved_with_reasons():
    stored = result()
    original = deepcopy(stored)
    shown = review_scope.adjust_article(item(stored, {"state": "pending", "general_pending": True}), article(), [TANGIER])
    assert shown["state"] == "done"
    assert shown["analysis"]["analysis_status"] == "done"
    assert shown["analysis"]["review_reasons"] == []
    assert "event_state_confidence_low" in shown["analysis"]["context_notes"]
    assert shown["review_scope"]["reasons"] == ["event_state_confidence_low"]
    assert shown["human_review"]["state"] == "not_required"
    # The stored analysis keeps its original status and reasons.
    assert stored == original


def test_risk_urgency_or_affected_supplier_keep_review():
    for extra in ({"is_risk": "Y"}, {"urgent": "Y"}, {"affected_supplier_ids": ["S040"]}):
        shown = review_scope.adjust_article(item(result(**extra)), article(), [TANGIER])
        assert shown["state"] == "review" and "review_scope" not in shown


def test_supplier_specific_doubt_keeps_review():
    cases = (
        result(review_reasons=["link_ambiguous:S040"]),
        result(assessments=[{"supplier_id": "S040", "needs_review": True}]),
        result(review_details=[{"supplier_id": "S040", "requires_review": True, "code": "x"}]),
    )
    for res in cases:
        assert review_scope.adjust_article(item(res), article(), [TANGIER])["state"] == "review"


def test_supplier_place_in_text_keeps_review():
    text = article("Wildfires near Tangier industrial zone prompt temporary factory closures")
    assert review_scope.adjust_article(item(result()), text, [TANGIER])["state"] == "review"


def test_started_human_work_and_other_states_are_untouched():
    for human in ({"state": "in_verification"}, {"state": "resolved"}):
        assert review_scope.adjust_article(item(result(), human), article(), [TANGIER])["state"] == "review"
    done = {"id": "a1", "state": "done", "analysis": result(analysis_status="done")}
    assert review_scope.adjust_article(done, article(), [TANGIER]) is done


def test_presenter_review_panel_matches_article_view():
    record = {"state": "pending", "general_pending": True}
    shown = review_scope.adjust_review(record, article(), result(), [TANGIER])
    assert shown["state"] == "not_required" and not shown["general_pending"]
    kept = review_scope.adjust_review(record, article(), result(is_risk="Y"), [TANGIER])
    assert kept is record
