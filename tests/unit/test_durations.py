"""Literal duration extraction; no labels, datasets, DB or network."""
import pytest
from app.duration import durations
from reference.jev_requests import stage_b


@pytest.mark.parametrize("text,days,lower", [
    ("two days", 2., False), ("dos días", 2., False),
    ("at least two days", 2., True), ("al menos dos días", 2., True),
    ("more than two days", 2., True), ("más de dos días", 2., True),
    ("Two DAYS", 2., False), ("2 days", 2., False),
    ("at least 2 days", 2., True), ("1.5 days", 1.5, False),
    ("two weeks", 14., False), ("dos semanas", 14., False),
    ("twelve months", 360., False), ("doce meses", 360., False),
])
def test_explicit_durations_preserve_span_and_bound(text, days, lower):
    assert durations({"summary": "Suspended for " + text + "."}) == [
        {"id": "d1", "text": text, "days": days, "lower_bound": lower}]


@pytest.mark.parametrize("text", [
    "until further notice", "indefinitely", "por tiempo indefinido",
    "several days", "varios días", "some weeks", "próximamente",
    "20 percent reduced capacity", "two days ago", "hace dos días",
    "two to three days", "entre dos y tres días", "up to two days",
    "about two days", "no more than two days", "fewer than two days",
    "not at least two days", "menos de dos días", "-2 days", "zero days",
    "0 days", "one hundred two days", "twenty two days",
    "twenty-two days", "2 to 3 days", "2 days to 3 days",
])
def test_no_fixed_duration_invented_for_unusable_period(text):
    assert durations({"summary": text}) == []


def test_missing_text_and_field_boundaries_never_create_duration():
    assert durations({"headline": None, "summary": None}) == []
    assert durations({"headline": "two", "summary": "days"}) == []
    assert durations({"headline": "two days", "summary": "dos días"}) == [
        {"id": "d1", "text": "two days", "days": 2., "lower_bound": False},
        {"id": "d2", "text": "dos días", "days": 2., "lower_bound": False}]


def test_candidate_reaches_effective_payload_but_is_not_selected_automatically():
    article = {"headline": "MOCK factories reduce production for at least two days"}
    candidates = durations(article)
    payload = stage_b(article, [{"supplier_id": "QA001", "name": "MOCK supplier"}], candidates)
    assert payload["state"]["duration_candidates"][0]["lower_bound"] is True
    assert payload["questions"]["duration_QA001"]["criteria"]["d1"] == {
        "text": "at least two days", "days": 2.}
    assert "unknown" in payload["questions"]["duration_QA001"]["criteria"]
    assert "numbers about another event" in payload["questions"]["duration_QA001"]["instructions"]


def test_duration_fix_is_reexported_and_changes_effective_cache_key():
    from app.analysis import durations as exported
    from app.importer import digest
    assert exported is durations
    article = {"headline": "MOCK factories reduce output for two days"}
    suppliers = [{"supplier_id": "QA001", "name": "MOCK supplier"}]
    old = stage_b(article, suppliers, [])
    new = stage_b(article, suppliers, durations(article))
    assert digest(old) != digest(new)


def test_directed_plan_is_ready_without_calls_or_evaluation_labels():
    import json
    from pathlib import Path
    from app.link_questions import stage_a, stage_b as experimental_b, select_candidates
    plan = json.loads(Path("reports/duration-directed-check.json").read_text())
    suppliers = [{"supplier_id": f"QA{i:03}", "name": f"MOCK supplier {i}",
        "city": "Hangzhou" if i == 24 else "Basel",
        "country": "China" if i == 24 else "Switzerland",
        "category": "Secondary packaging", "material": "MOCK leaflets",
        "criticality": "Low", "single_source": "N", "alternate_id": None,
        "lead_days": 25, "inventory_days": 30, "share_category_pct": 1} for i in range(1, 41)]
    assert plan["status"] == "prepared_not_executed"
    assert len(plan["cases"]) == 6
    assert plan["maximum_requests_including_retries"] == len(plan["cases"]) * 2 * 3
    for case in plan["cases"]:
        article = case["article"]
        candidates = durations(article)
        assert candidates == [{"id": "d1", **case["expected_candidate"]}]
        a = stage_a(article, suppliers, plan["model"])
        assert len([k for k in a["questions"] if k.startswith("candidate_")]) == 40
        mock_a = {"answers": {"candidate_" + s["supplier_id"]: {"noul": .9 if s["supplier_id"] == "QA024" else .02} for s in suppliers}}
        selected = select_candidates(article, suppliers, mock_a)
        assert [s["supplier_id"] for s in selected] == ["QA024"]
        b = experimental_b(article, selected, candidates, plan["model"])
        assert b["state"]["duration_candidates"][0]["lower_bound"] == case["expected_candidate"]["lower_bound"]
        assert not {"Is_Risk", "Urgent", "Affected_Supplier_IDs", "Event_Type", "Explanation", "expected_candidate"} & b["state"]["article"].keys()
