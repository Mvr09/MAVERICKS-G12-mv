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
