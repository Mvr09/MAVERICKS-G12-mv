"""Synthetic and explicitly mocked cases; no held-out labels or live inference."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analysis import process_article
from app.db import Session
from app.main import app
from app.models import Alert, Incident
from app.rss_questions import EVENT_CRITERIA, EVENT_LABELS, stage_a, VERSION
from app.settings import POLICY, settings
from reference.jev_requests import stage_a as exercise_a
from tests.helpers import synthetic, answer


@pytest.mark.parametrize("category", list(EVENT_LABELS))
def test_every_discrete_rss_category_roundtrips_without_changing_canonical_contract(category):
    with Session() as db:
        a = synthetic(db, "MOCK taxonomy case", "MOCK independent synthetic event.")
        a.context = "rss"
        a.batch_id = None
        db.commit()
        result = process_article(db, a.id, httpx.MockTransport(
            lambda r: httpx.Response(200, json=answer(json.loads(r.content), linked=(), event=category))
        ))
        assert result["question_version"] == VERSION
        assert result["event_classification"]["category"] == category
        assert result["event_classification"]["label_es"] == EVENT_LABELS[category]
        assert result["event_type"] == ("natural_disaster" if category == "wildfire" else category)


def test_taxonomy_has_closed_boundaries_and_exercise_payload_is_unchanged():
    article = {"headline": "MOCK: port strike", "summary": "MOCK workers stop work."}
    before = exercise_a(article, [], settings.jev_model)
    rss = stage_a(article, [], settings.jev_model)
    assert set(EVENT_CRITERIA) == set(EVENT_LABELS) == set(POLICY["event_types"]) | {"wildfire"}
    assert rss["questions"]["event_type"]["criteria"] == EVENT_CRITERIA
    assert "port strike is labour_strike" in rss["questions"]["event_type"]["instructions"]
    assert "report uncertainty" in rss["questions"]["event_type"]["instructions"]
    assert "Excludes price-only" in EVENT_CRITERIA["logistics_disruption"]
    assert "Never select merely" in EVENT_CRITERIA["not_relevant"]
    assert exercise_a(article, [], settings.jev_model) == before
    assert before["questions"]["event_type"]["criteria"] == POLICY["event_types"]


def test_alerts_and_incident_headlines_keep_precise_type_including_legacy_records():
    with Session() as db:
        a = synthetic(db, "MOCK wildfire", "MOCK forest fire halts production for 14 days.")
        a.context = "rss"
        a.batch_id = None
        db.commit()
        process_article(db, a.id, httpx.MockTransport(
            lambda r: httpx.Response(200, json=answer(json.loads(r.content), linked=("S001",), event="wildfire"))
        ))
        alert = db.scalar(select(Alert))
        incident = db.scalar(select(Incident))
        assert alert.data["event_tag"]["event_classification"]["category"] == "wildfire"
        assert incident.history[-1]["event_tag"]["event_classification"]["category"] == "wildfire"
        # Simulate records from before metadata was saved, without reanalysis.
        alert.data = {k: v for k, v in alert.data.items() if k != "event_tag"}
        incident.history = [{k: v for k, v in h.items() if k != "event_tag"} for h in incident.history]
        db.commit()
    with TestClient(app) as c:
        alerts = c.get("/api/alerts?context=rss").json()["items"]
        supplier = c.get("/api/suppliers/S001?context=rss").json()
        assert alerts[0]["event_tag"]["event_classification"]["category"] == "wildfire"
        assert supplier["incidents"][0]["event_tag"]["event_classification"]["category"] == "wildfire"
        assert "assessments" not in alerts[0]["event_tag"]
