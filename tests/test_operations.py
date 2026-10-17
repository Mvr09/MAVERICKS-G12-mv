from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, func, delete
from app.db import Session
from app.main import app
from app.models import Source, Job, WorkerPresence, Grant, GrantArticle, Article, now
from app.settings import settings
from app.cli import seed
from app.queue import enqueue_rss_analysis, reserve
from app.worker import pulse
from tests.helpers import synthetic


def login(client):
    response = client.post(
        "/api/session", json={"password": settings.admin_password.get_secret_value()}
    )
    assert response.status_code == 200
    return {"x-csrf-token": response.json()["csrf"]}


def test_sync_initializes_sources_deduplicates_and_reports_missing_worker():
    with Session() as db:
        db.execute(delete(Source))
        db.commit()
    with TestClient(app) as c:
        headers = login(c)
        first = c.post("/api/sources/sync", headers=headers)
        second = c.post("/api/sources/sync", headers=headers)
        assert first.status_code == second.status_code == 202
        assert first.json()["worker"]["online"] is False
        assert set(first.json()["job_ids"]) == set(second.json()["job_ids"])
        sources = c.get("/api/sources").json()
        assert len(sources) == 6
        assert all(
            s["job_state"] == "queued" and s["last_attempt_at"] is None for s in sources
        )
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 6


def test_worker_presence_expires_and_recovers():
    c = TestClient(app)
    pulse("MOCK-WORKER")
    assert c.get("/api/worker").json()["online"] is True
    with Session() as db:
        db.get(WorkerPresence, "MOCK-WORKER").heartbeat = now() - timedelta(seconds=31)
        db.commit()
    assert c.get("/api/worker").json()["online"] is False
    pulse("MOCK-WORKER")
    assert c.get("/api/worker").json()["online"] is True


def test_manual_rss_budget_is_bounded_without_enabling_periodic_analysis():
    assert not settings.rss_analysis_enabled
    with Session() as db:
        # Isolate a synthetic grant, never call the provider.
        db.execute(delete(Grant).where(Grant.split == "rss"))
        db.add(
            Grant(
                id="MOCK-RSS-TWO",
                split="rss",
                article_limit=2,
                expires_at=now() + timedelta(hours=1),
            )
        )
        rows = [synthetic(db, headline=f"MOCK RSS {i}") for i in range(3)]
        for a in rows:
            a.context = "rss"
        db.commit()
        assert not reserve(db, rows[0], "rss")
        assert len(enqueue_rss_analysis(db, 10)) == 2
        db.commit()
    with Session() as db:
        assert enqueue_rss_analysis(db, 10) == []
        assert db.get(Grant, "MOCK-RSS-TWO").used == 2
        assert db.scalar(select(func.count()).select_from(GrantArticle)) == 2
        # Seeding an existing authorization cannot reset its usage.
        seeded = db.get(Grant, "initial-training-3")
        seeded.used = 3
        db.commit()
        seed(db)
        db.commit()
        assert seeded.used == 3


def test_rss_analysis_requires_presenter_and_connected_worker():
    with TestClient(app) as c:
        assert c.post("/api/analysis/rss", json={"limit": 10}).status_code == 401
        headers = login(c)
        assert (
            c.post("/api/analysis/rss", headers=headers, json={"limit": 11}).status_code
            == 422
        )
        response = c.post("/api/analysis/rss", headers=headers, json={"limit": 10})
        assert response.status_code == 409
        assert "worker" in response.json()["message"]


def test_cleanup_only_training_and_liveday_preserves_catalog_rss_and_consumption():
    from app.models import Supplier, Material, Batch, ApiCall, RequestCache

    with Session() as db:
        training = db.scalar(select(Batch).where(Batch.split == "training"))
        target = db.scalar(select(Article).where(Article.batch_id == training.id))
        db.get(Grant, "initial-training-3").used = 3
        db.add(GrantArticle(article_id=target.id, grant_id="initial-training-3"))
        db.add(
            ApiCall(
                article_id=target.id,
                stage="a",
                attempt=1,
                model="MOCK",
                status=200,
                duration=0,
                usage={},
            )
        )
        db.add(RequestCache(id="MOCK-CACHE", response={"mock": True}))
        db.add(
            Article(
                id="MOCK-RSS-KEEP",
                origin_key="MOCK-RSS-KEEP",
                context="rss",
                news_id="MOCK",
                content_hash="MOCK",
                data={"headline": "MOCK RSS"},
                state="pending",
            )
        )
        db.commit()
    with TestClient(app) as c:
        assert c.get("/api/demo/cleanup-preview").status_code == 401
        headers = login(c)
        preview = c.get("/api/demo/cleanup-preview").json()
        assert preview["counts"]["articles"] == 44
        assert preview["blocked"] is None
        response = c.post(
            "/api/demo/cleanup",
            headers=headers,
            json={"confirmation": "LIMPIAR DEMO", "token": preview["token"]},
        )
        assert response.status_code == 200
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Supplier)) == 40
        assert db.scalar(select(func.count()).select_from(Material)) == 20
        assert {b.split for b in db.scalars(select(Batch))} == {"validation", "test"}
        assert db.scalar(select(func.count()).select_from(Article)) == 31
        assert db.get(Article, "MOCK-RSS-KEEP") is not None
        assert db.get(Grant, "initial-training-3").used == 3
        assert db.scalar(select(func.count()).select_from(ApiCall)) == 1
        assert db.get(RequestCache, "MOCK-CACHE") is not None


def test_cleanup_rejects_stale_preview_running_job_and_shared_incident():
    from app.models import Batch, Incident
    from app.demo import preview, cleanup
    import pytest

    with Session() as db:
        old = preview(db)
        target = synthetic(db, headline="MOCK added after preview")
        with pytest.raises(ValueError, match="cambiado"):
            cleanup(db, old["token"])
        db.rollback()
        db.add(
            Job(
                key="analysis:" + target.id,
                kind="analysis",
                payload={"article_id": target.id},
                state="running",
            )
        )
        db.commit()
        assert "curso" in preview(db)["blocked"]
        db.execute(delete(Job))
        validation = db.scalar(select(Batch).where(Batch.split == "validation"))
        retained = db.scalar(select(Article).where(Article.batch_id == validation.id))
        db.add(
            Incident(
                context="exercise",
                supplier_id="S001",
                event_type="other",
                signature="MOCK",
                state="active",
                priority=1,
                historical_priority=1,
                event_date="2026-10-17",
                history=[{"article_id": target.id}, {"article_id": retained.id}],
            )
        )
        db.commit()
        p = preview(db)
        assert "compartidos" in p["blocked"]
        with pytest.raises(ValueError, match="compartidos"):
            cleanup(db, p["token"])
        db.rollback()
        assert db.get(Article, target.id) is not None


def test_provider_authentication_error_blocks_further_calls_in_the_same_grant():
    from app.jev import grant_requires_diagnosis
    from app.models import ApiCall

    with Session() as db:
        a = synthetic(db)
        db.add(GrantArticle(article_id=a.id, grant_id="initial-training-3"))
        db.add(
            ApiCall(
                article_id=a.id,
                stage="a",
                attempt=1,
                model="MOCK",
                status=401,
                duration=0,
                usage={"_error": "JEV_HTTP_401"},
            )
        )
        db.commit()
        assert grant_requires_diagnosis(db, "initial-training-3")
        assert not grant_requires_diagnosis(
            db, "initial-training-3", now() + timedelta(seconds=1)
        )
