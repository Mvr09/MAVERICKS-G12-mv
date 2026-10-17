"""Operaciones seleccionadas sobre PostgreSQL aislado; JEV usa transporte mock."""

import json
from datetime import timedelta
import httpx
import pytest
from sqlalchemy import select, func
from app.db import Session
from app.cli import seed
from app.models import (
    Article,
    Batch,
    Analysis,
    ApiCall,
    Grant,
    GrantArticle,
    RssDailyUsage,
    Incident,
    Alert,
    Draft,
    Source,
    Job,
    Comparison,
    now,
)
from app.demo import preview, cleanup, options
from app.analysis import process_article
from app.comparison import enqueue_comparison, process_comparison
from app.views import article_view, suppliers_view
from app.queue import reserve
from app.importer import export_batch
from tests.helpers import synthetic, answer


def test_selection_deletes_only_chosen_batch_and_can_reimport():
    from pathlib import Path
    from app.importer import import_excel

    with Session() as db:
        target = db.scalar(select(Batch).where(Batch.split == "validation"))
        untouched = set(
            db.scalars(select(Article.id).where(Article.batch_id != target.id))
        )
        token = preview(db, ["batch:" + target.id])["token"]
        cleanup(db, token)
        db.commit()
        assert db.get(Batch, target.id) is None
        assert set(db.scalars(select(Article.id))) == untouched
        batch, diagnostic = import_excel(
            db,
            Path("inputs/supplier_validation.xlsx").read_bytes(),
            "supplier_validation.xlsx",
        )
        db.commit()
        assert batch.count == 10 and not diagnostic.get("idempotent")
        assert (
            len(db.scalars(select(Article).where(Article.batch_id == batch.id)).all())
            == 10
        )


def test_selected_shared_incident_retains_other_evidence_and_visual_notice():
    with Session() as db:
        a = synthetic(db)
        b = synthetic(db, headline="MOCK retained")
        assessment = {
            "impact_status": "active",
            "priority": 72,
            "urgent": "Y",
            "needs_review": False,
            "priority_band": "high",
        }
        incident = Incident(
            context="exercise",
            supplier_id="S001",
            event_type="fire_incident",
            signature="MOCK",
            state="active",
            priority=90,
            historical_priority=90,
            event_date="2026-10-02",
            history=[
                {
                    "article_id": a.id,
                    "published_date": "2026-10-02",
                    "at": "2026-10-02",
                    "headline": "MOCK delete",
                    "assessment": {**assessment, "priority": 90},
                },
                {
                    "article_id": b.id,
                    "published_date": "2026-10-01",
                    "at": "2026-10-01",
                    "headline": "MOCK retained",
                    "assessment": assessment,
                },
            ],
        )
        db.add(incident)
        db.commit()
        old_id = incident.id
        p = preview(db, ["batch:" + a.batch_id])
        assert not p["blocked"]
        cleanup(db, p["token"])
        db.commit()
        retained = db.get(Incident, old_id)
        assert retained.priority == retained.historical_priority == 72
        assert [h["article_id"] for h in retained.history] == [b.id]
        assert db.get(Article, b.id) is not None
        notice = db.scalar(select(Alert).where(Alert.incident_id == old_id))
        assert notice and not notice.data["sound_eligible"]


def test_rerun_archives_results_bypasses_cache_and_preserves_attempts():
    calls = []
    linked = ["S001"]

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=answer(calls[-1], linked=linked))

    transport = httpx.MockTransport(handle)
    with Session() as db:
        seed(db)
        a = synthetic(db)
        first = process_article(db, a.id, transport=transport)
        old = db.scalar(select(Analysis).where(Analysis.article_id == a.id))
        old_id = old.id
        old_calls = db.scalar(
            select(func.count()).select_from(ApiCall).where(ApiCall.article_id == a.id)
        )
        p = preview(db, ["article:" + a.id], "rerun")
        assert not p["blocked"]
        result = cleanup(db, p["token"])
        db.commit()
        assert len(result["job_ids"]) == 1 and a.generation == 1
        assert db.get(Analysis, old_id).result == first
        assert article_view(db, a)["analysis"] is None
        with pytest.raises(ValueError, match="bloqueada"):
            export_batch(db, a.batch_id)
        linked[:] = ["S002"]
        second = process_article(db, a.id, transport=transport)
        assert second["affected_supplier_ids"] == ["S002"]
        assert len(calls) == 4
        assert (
            db.scalar(
                select(func.count())
                .select_from(ApiCall)
                .where(ApiCall.article_id == a.id, ApiCall.run_key == "")
            )
            == old_calls
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Analysis)
                .where(Analysis.article_id == a.id)
            )
            == 2
        )
        assert article_view(db, a)["analysis"] == second
        assert (
            next(s for s in suppliers_view(db) if s["supplier_id"] == "S001")["status"]
            == "pending"
        )
        process_article(db, a.id, transport=transport)
        assert len(calls) == 4  # Reclamación del mismo trabajo no repite inferencia.


def test_rss_delete_preserves_daily_accounting_and_resets_conditional_fetch():
    with Session() as db:
        seed(db)
        source = db.scalar(select(Source))
        source.etag = "MOCK-ETAG"
        source.modified = "MOCK"
        a = synthetic(db)
        a.context = "rss"
        a.source_id = source.id
        assert reserve(db, a, "rss", manual_rss=True)
        db.commit()
        before = db.scalar(select(func.count()).select_from(RssDailyUsage))
        grant_id = db.get(GrantArticle, a.id).grant_id
        used = db.get(Grant, grant_id).used
        p = preview(db, ["rss:" + source.id])
        cleanup(db, p["token"])
        db.commit()
        assert db.get(Article, a.id) is None
        assert db.scalar(select(func.count()).select_from(RssDailyUsage)) == before
        assert db.get(Grant, grant_id).used == used
        assert source.etag is None and source.modified is None


def test_selection_and_preview_cannot_be_replayed_or_affected_while_running():
    with Session() as db:
        a = synthetic(db)
        p = preview(db, ["article:" + a.id])
        a.data = {**a.data, "summary": "changed"}
        a.content_hash = "changed"
        db.commit()
        with pytest.raises(ValueError, match="cambiado"):
            cleanup(db, p["token"])
        db.rollback()
        db.add(
            Job(
                key="MOCK-COMPARISON",
                kind="comparison",
                payload={"article_id": a.id},
                state="running",
            )
        )
        db.commit()
        assert "curso" in preview(db, ["article:" + a.id])["blocked"]
        assert "todas" in preview(db, ["catalog"])["blocked"]


def test_three_votes_are_fresh_persistent_and_do_not_change_original_or_exports():
    calls = []

    def handle(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(200, json=answer(payload, linked=(), confidence=0.45))

    transport = httpx.MockTransport(handle)
    with Session() as db:
        seed(db)
        a = synthetic(db)
        a.context = "rss"
        a.batch_id = None
        db.commit()
        original = process_article(db, a.id, transport=transport)
        original_view = article_view(db, a)
        comparison, job = enqueue_comparison(db, a.id)
        db.commit()
        same, samejob = enqueue_comparison(db, a.id)
        assert same.id == comparison.id and samejob.id == job.id
        result = process_comparison(db, comparison.id, transport=transport)
        assert result.state == "done" and len(result.ballots) == 3
        assert (
            len(calls) == 4
        )  # Original + tres consultas nuevas; nunca tres lecturas de caché.
        assert result.summary["review_votes"] == 3 and result.summary["done_votes"] == 0
        assert result.summary["advisory_only"]
        assert a.state == "review" and article_view(db, a)["analysis"] == original
        assert article_view(db, a)["analysis"] == original_view["analysis"]
        assert (
            db.scalar(
                select(func.count())
                .select_from(Analysis)
                .where(Analysis.article_id == a.id)
            )
            == 1
        )
        process_comparison(db, comparison.id, transport=transport)
        assert len(calls) == 4


def test_contrast_does_not_turn_provider_failure_into_negative_vote():
    def handle(request):
        return httpx.Response(401)

    with Session() as db:
        seed(db)
        a = synthetic(db)
        a.context = "rss"
        a.batch_id = None
        a.state = "review"
        db.commit()
        comparison, _ = enqueue_comparison(db, a.id)
        db.commit()
        result = process_comparison(
            db, comparison.id, transport=httpx.MockTransport(handle)
        )
        assert result.state == "error" and len(result.ballots) == 1
        assert result.ballots[0]["is_risk"] is None
        assert result.summary["errors"] == 1 and result.summary["done_votes"] == 0


def test_new_management_endpoints_require_presenter_and_mode_bound_confirmation():
    from fastapi.testclient import TestClient
    from app.main import app
    from tests.test_operations import login

    with TestClient(app) as client:
        assert client.get("/api/demo/options").status_code == 401
        assert (
            client.post("/api/demo/preview", json={"selection": []}).status_code == 401
        )
        assert client.get("/api/articles/mock/runs").status_code == 401
        assert client.get("/api/articles/mock/comparisons").status_code == 401
        assert client.post("/api/articles/mock/compare").status_code == 401
        headers = login(client)
        with Session() as db:
            b = db.scalar(select(Batch).where(Batch.split == "validation"))
            bid = b.id
            article = db.scalar(select(Article).where(Article.batch_id == bid))
            aid = article.id
            db.add(Comparison(article_id=aid))
            db.commit()
        rows = client.get("/api/articles/" + aid + "/comparisons").json()
        assert len(rows) == 1 and rows[0]["network_requests"] == 0
        p = client.post(
            "/api/demo/preview", headers=headers, json={"selection": ["batch:" + bid]}
        ).json()
        assert not p["blocked"]
        assert (
            client.post(
                "/api/demo/cleanup",
                headers=headers,
                json={"token": p["token"], "confirmation": "REANALIZAR"},
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/demo/cleanup",
                headers=headers,
                json={"token": "forged", "confirmation": "LIMPIAR DEMO"},
            ).status_code
            == 409
        )
        with Session() as db:
            assert db.get(Batch, bid) is not None
