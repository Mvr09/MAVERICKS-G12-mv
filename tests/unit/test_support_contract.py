"""Synthetic support/polarity regressions; no provider, DB or dataset access."""
from types import SimpleNamespace

import pytest

from app.link_analysis import normalize
from app.link_questions import stage_b
from app.settings import POLICY


SUPPLIER = {
    "supplier_id": "QA001", "name": "Proveedor sintético", "country": "China",
    "city": "Hangzhou", "category": "Secondary packaging", "material": "Leaflets",
    "criticality": "Low", "single_source": "N", "alternate_id": None,
    "lead_days": 25, "inventory_days": 30, "share_category_pct": 1,
}
ARTICLE = SimpleNamespace(id="synthetic", news_id="QA-support", context="exercise",
    data={"headline": "MOCK industrial event", "summary": "MOCK source fact."})


def evaluate(*, linked=True, association=.95, risk_support=.95, citation=True,
             risk_citation=True, citation_confidence=.95, risk=.9, urgent=.1):
    a = {"model": "jev-1.13.0", "answers": {
        "event_type": {"choice": "utility_outage", "confidence": .95},
        "event_state": {"choice": "active", "confidence": .95},
        "article_threat": {"noul": .9}, "candidate_QA001": {"noul": .9},
    }}
    b = {"answers": {}}
    for field, value in {"identity": .02, "area": .9 if linked else .02,
        "operation": .9 if linked else .02, "association_support": association,
        "risk_support": risk_support, "risk": risk, "urgent": urgent}.items():
        b["answers"][field + "_QA001"] = {"type": "noul", "noul": value}
    for field, choice, confidence in [
        ("link_evidence", "e1" if citation else "none", citation_confidence),
        ("evidence", "e2" if risk_citation else "none", citation_confidence),
        ("impact_state", "active", .95), ("duration", "unknown", 1.),
    ]:
        b["answers"][field + "_QA001"] = {"type": "choice", "choice": choice, "confidence": confidence}
    b["answers"]["severity_QA001"] = {"type": "score", "score": 3., "confidence": .95}
    return normalize(ARTICLE, [SUPPLIER], a, b, [])


@pytest.mark.parametrize("field", ["association", "risk_support"])
@pytest.mark.parametrize("support,review", [(0., True), (.35, True), (.65, True), (.6501, False), (1., False)])
def test_support_uses_positive_noul_and_excludes_ambiguous_boundary(field, support, review):
    result = evaluate(**{field: support})
    assert (result["analysis_status"] == "review") is review
    assert result["is_risk"] == "Y"  # Support never flips the binary risk gate.


def test_selected_citation_is_not_sufficient_support():
    result = evaluate(association=.2, risk_support=.2, citation_confidence=1.)
    assert set(result["review_reasons"]) == {
        "association_support_insufficient:QA001", "risk_evidence_insufficient:QA001"}


def test_high_support_without_literal_anchor_still_reviews():
    result = evaluate(citation=False, risk_citation=False)
    assert result["analysis_status"] == "review"
    assert len(result["review_reasons"]) == 2


def test_weak_choice_confidence_is_auxiliary_when_support_and_anchors_exist():
    result = evaluate(citation_confidence=.1)
    assert result["analysis_status"] == "done"
    assert result["context_notes"]
    assert all(not d["requires_review"] for d in result["review_details"])


def test_absent_link_is_not_proof_of_exclusion():
    result = evaluate(linked=False, association=.2, risk=.99)
    assert result["affected_supplier_ids"] == []
    assert result["is_risk"] == result["urgent"] == "N"
    assert result["analysis_status"] == "review"
    assert result["assessments"][0]["association_status"] == "review"


def test_supported_exclusion_does_not_need_conditional_risk_support():
    result = evaluate(linked=False, association=.95, risk_support=.1, risk_citation=False)
    assert result["analysis_status"] == "done"
    assert result["assessments"][0]["association_status"] == "excluded"
    assert result["is_risk"] == result["urgent"] == "N"


def test_supported_negative_risk_keeps_positive_identity_or_exposure():
    result = evaluate(risk=.02)
    assert result["affected_supplier_ids"] == ["QA001"]
    assert result["is_risk"] == result["urgent"] == "N"
    assert result["analysis_status"] == "done"


def test_effective_payload_distinguishes_support_from_citation_and_uses_catalog():
    payload = stage_b(ARTICLE.data, [SUPPLIER], [], "jev-1.13.0")
    q = payload["questions"]
    assert not any(k.startswith(("scope_and_link_evidence", "risk_evidence")) for k in q)
    for field in ("association_support", "risk_support"):
        question = q[field + "_QA001"]
        assert question["type"] == "noul"
        assert question["instructions"]["supplier"]["material"] == "Leaflets"
        assert question["instructions"]["geography"]["status"] == "matched"
    assert "clearly exclude" in q["association_support_QA001"]["instructions"]["question"]
    assert "negative decision" in q["risk_support_QA001"]["instructions"]["question"]
    for field in ("link_evidence", "evidence"):
        assert q[field + "_QA001"]["type"] == "choice"
        assert "none" in q[field + "_QA001"]["criteria"]
    assert POLICY["thresholds"]["review_high"] == .65


def test_wire_contract_accepts_noul_without_choice_confidence():
    from app.jev import validate_response
    payload = {"model": "jev-1.13.0", "questions": {"association_support_QA001": {"type": "noul"}}}
    data = {"model": payload["model"], "usage": {}, "answers": {
        "association_support_QA001": {"type": "noul", "noul": .9}}}
    assert validate_response(payload, data)["answers"]["association_support_QA001"]["noul"] == .9


def test_wire_contract_never_substitutes_confidence_for_missing_noul():
    from app.jev import validate_response, ProviderError
    payload = {"model": "jev-1.13.0", "questions": {"risk_support_QA001": {"type": "noul"}}}
    data = {"model": payload["model"], "usage": {}, "answers": {
        "risk_support_QA001": {"type": "noul", "confidence": .99}}}
    with pytest.raises(ProviderError, match="CONTRACT_RANGE"):
        validate_response(payload, data)
