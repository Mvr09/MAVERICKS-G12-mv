"""Calidad y telemetría con mocks identificados; no llamadas externas."""

import json
import httpx
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.db import Session
from app.main import app
from app.models import Article, Analysis, EvaluationLabel, ApiCall, Batch
from app.evaluation import evaluate_batch, metrics
from app.model_metrics import model_metrics, percentiles
from app.analysis import process_article
from app.rss_questions import stage_a, VERSION
from app.views import article_view
from app.settings import settings, POLICY
from reference.jev_requests import stage_a as exercise_a
from tests.helpers import synthetic, answer
from tests.test_operations import login


def test_metrics_undefined_denominators_and_review_subsets():
    pair = (
        {"Is_Risk": "N", "Urgent": "N", "Affected_Supplier_IDs": ""},
        {
            "is_risk": "N",
            "urgent": "N",
            "affected_supplier_ids": [],
            "analysis_status": "review",
        },
    )
    result = metrics([pair])
    assert (
        result["risk"]["precision"] is None
        and result["risk"]["recall"] is None
        and result["risk"]["f1"] is None
    )
    assert result["suppliers"]["exact_set_accuracy"] == 1
    assert result["review_count"] == 1
    assert percentiles([1, 2, 3])["p95"] == pytest.approx(2.9)
    assert percentiles([])["p50"] is None


def test_quality_and_execution_are_private_readonly_and_scoped():
    with Session() as db:
        a = synthetic(db)
        db.add(
            EvaluationLabel(
                article_id=a.id,
                data={"Is_Risk": "Y", "Urgent": "Y", "Affected_Supplier_IDs": "S001"},
            )
        )
        db.commit()
        process_article(
            db,
            a.id,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), linked=("S001",))
                )
            ),
        )
        db.add(
            ApiCall(
                article_id=a.id,
                stage="a",
                attempt=2,
                model=settings.jev_model,
                status=429,
                duration=2,
                usage={},
            )
        )
        db.commit()
        bid = a.batch_id
        before = db.scalar(select(func.count()).select_from(ApiCall))
    with TestClient(app) as c:
        assert c.get("/api/model/metrics").status_code == 401
        login(c)
        for _ in range(2):
            r = c.get("/api/model/metrics?context=exercise&origin=batch:" + bid)
            assert r.status_code == 200
            body = r.json()
            quality = next(b for b in body["evaluations"] if b["id"] == bid)
            assert quality["metrics"]["risk"]["f1"] == 1
            assert quality["metrics"]["automatic_coverage"] == 1
            assert quality["metrics"]["automatic"]["n"] == 1
            assert quality["metrics"]["under_review"] is None
            assert (
                body["execution"]["requests"] == 3 and body["execution"]["retries"] == 1
            )
            assert body["execution"]["failed_requests"] == 1
            assert body["execution"]["calls_with_token_usage"] == 2
            assert body["execution"]["article_count"] == 1
            assert not {
                "Is_Risk",
                "Urgent",
                "Affected_Supplier_IDs",
                "Explanation",
            } & set(json.dumps(body).split('"'))
            test = next(b for b in body["evaluations"] if b["split"] == "test")
            assert test["status"] == "unlabelled" and test["metrics"] is None
        assert (
            c.get("/api/model/metrics?context=rss").json()["execution"]["requests"] == 0
        )
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(ApiCall)) == before


def test_quality_rejects_mixed_versions_in_same_batch():
    with Session() as db:
        a = synthetic(db)
        b = synthetic(db, headline="MOCK IDENTIFICADO: segundo caso")
        b.batch_id = a.batch_id
        db.get(Batch, a.batch_id).count = 2
        for row in (a, b):
            db.add(
                EvaluationLabel(
                    article_id=row.id,
                    data={
                        "Is_Risk": "Y",
                        "Urgent": "Y",
                        "Affected_Supplier_IDs": "S001",
                    },
                )
            )
        db.commit()
        for row in (a, b):
            process_article(
                db,
                row.id,
                httpx.MockTransport(
                    lambda r: httpx.Response(
                        200, json=answer(json.loads(r.content), linked=("S001",))
                    )
                ),
            )
        analysis = db.scalar(select(Analysis).where(Analysis.article_id == b.id))
        analysis.result = {**analysis.result, "question_version": "MOCK-OTHER-VERSION"}
        db.commit()
        with pytest.raises(ValueError, match="versiones mezcladas"):
            evaluate_batch(db, a.batch_id)
        item = next(
            row
            for row in model_metrics(db, "exercise")["evaluations"]
            if row["id"] == a.batch_id
        )
        assert item["status"] == "unavailable" and item["metrics"] is None


@pytest.mark.parametrize(
    "event,canonical",
    [
        ("wildfire", "natural_disaster"),
        ("fire_incident", "fire_incident"),
        ("natural_disaster", "natural_disaster"),
    ],
)
def test_rss_explicit_fire_taxonomy_preserves_canonical_contract(event, canonical):
    payloads = []

    def fetch(request):
        p = json.loads(request.content)
        payloads.append(p)
        return httpx.Response(
            200, json=answer(p, linked=(), event=event, confidence=0.98)
        )

    with Session() as db:
        a = synthetic(
            db, headline="MOCK IDENTIFICADO: explicit event category " + event
        )
        a.context = "rss"
        a.batch_id = None
        db.commit()
        result = process_article(db, a.id, httpx.MockTransport(fetch))
        assert result["event_type"] == canonical
        assert result["event_classification"]["category"] == event
        assert result["event_classification"]["confidence"] == 0.98
        assert result["question_version"] == VERSION
        assert "event_type_confidence_low" not in result["context_notes"]
        assert (
            "forest" in payloads[0]["questions"]["event_type"]["criteria"]["wildfire"]
        )
        assert (
            "Excludes forest"
            in payloads[0]["questions"]["event_type"]["criteria"]["fire_incident"]
        )
        assert (
            "wildfire"
            not in exercise_a(a.data, [], settings.jev_model)["questions"][
                "event_type"
            ]["criteria"]
        )
        assert article_view(db, a)["event_type_confidence"] == 0.98
    with TestClient(app) as client:
        assert (
            len(client.get("/api/articles?context=rss&event_type=" + event).json()) == 1
        )


def test_ingestion_reason_counts_deduplicate_supplier_reasons():
    with Session() as db:
        a = synthetic(db)
        process_article(
            db,
            a.id,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), confidence=0.4)
                )
            ),
        )
    with TestClient(app) as c:
        overview = c.get("/api/overview").json()
        reason = next(
            r
            for r in overview["review_reasons"]
            if r["reason"] == "severity_confidence_low"
        )
        assert reason["articles"] == 1  # dos proveedores, una noticia
        assert overview["review_rate"] == 1 and overview["automatic_rate"] == 0


def test_gdacs_publisher_code_is_traceable_evidence_not_a_risk_override():
    article = {
        "headline": "Green forest fire notification",
        "summary": "MOCK public source",
        "source": "GDACS",
        "url": "https://www.gdacs.org/report.aspx?eventtype=WF&eventid=MOCK",
        "Is_Risk": "PROTECTED",
    }
    payload = stage_a(article, [], settings.jev_model)
    assert payload["state"]["publisher_metadata"]["event_code"] == "WF"
    assert (
        "does not establish supplier exposure"
        in payload["state"]["publisher_metadata"]["limitation"]
    )
    assert "PROTECTED" not in json.dumps(payload)
    foreign = stage_a(
        {**article, "url": "https://example.org/report?eventtype=WF"},
        [],
        settings.jev_model,
    )
    assert "publisher_metadata" not in foreign["state"]
    other = stage_a({**article, "source": "Other publisher"}, [], settings.jev_model)
    assert "publisher_metadata" not in other["state"]


def test_execution_current_versions_exclude_superseded_and_inflight_is_not_error():
    with Session() as db:
        a = synthetic(db)
        a.context = "rss"
        a.batch_id = None
        a.source_id = "gdacs"
        db.commit()
        process_article(
            db,
            a.id,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), linked=())
                )
            ),
        )
        newest = Article(
            origin_key=a.origin_key,
            version=2,
            context="rss",
            source_id="gdacs",
            news_id=a.news_id,
            data={**a.data, "summary": "MOCK IDENTIFICADO: revised source"},
            content_hash="MOCK-VERSION-TWO",
        )
        db.add(newest)
        db.flush()
        db.add(
            ApiCall(
                article_id=newest.id,
                stage="a",
                attempt=1,
                model=settings.jev_model,
                status=None,
                duration=0,
                usage={},
            )
        )
        db.commit()
        e = model_metrics(db, "rss", "rss:gdacs")["execution"]
        assert e["article_count"] == 1 and e["retained_article_versions"] == 2
        assert e["latest_analysis_count"] == 0 and e["versions"] == []
        assert e["requests"] == 2 and e["inflight_requests"] == 1
        assert e["failed_requests"] == 0 and e["http_latency"]["n"] == 1
