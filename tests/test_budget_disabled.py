"""Permiso vigente sin presupuesto: mocks, ninguna llamada JEV de pago."""

import json, time
from datetime import timedelta
import httpx
from pydantic import SecretStr
from sqlalchemy import select, func
from app.settings import settings, RSS, AUTHORIZATION
from app.cli import seed
from app.db import Session
from app.models import (
    Article,
    RssDailyUsage,
    ConsumptionBudget,
    Grant,
    GrantArticle,
    ApiCall,
    now,
    Supplier,
)
from app.queue import reserve, enqueue_rss_analysis, budget_available
from app.jev import reserve_request, JevClient
from app.main import analysis_budget, budget_status
from reference.jev_requests import stage_a
from tests.helpers import synthetic, answer


def test_daily_cap_and_batch_cap_do_not_block_queue_and_periodic_stays_off(monkeypatch):
    monkeypatch.setattr(settings, "jev_budget_limits_enabled", False)
    assert AUTHORIZATION["budget_limits_enabled"] is False
    with Session() as db:
        seed(db)
        for n in range(RSS["daily_analysis_budget"]):
            db.add(RssDailyUsage(id=f"MOCK-OLD-DAY-{n}"))
        rows = []
        for n in range(RSS["daily_analysis_budget"] + 1):
            a = Article(
                origin_key=f"MOCK-UNLIMITED-{n}",
                context="rss",
                news_id=f"MOCK-{n}",
                content_hash=f"MOCK-{n}",
                data={"headline": "MOCK RSS"},
                state="pending",
            )
            db.add(a)
            rows.append(a)
        db.commit()
        assert not reserve(
            db, rows[0], "rss"
        )  # Pago periódico no autorizado por quitar presupuesto.
        jobs = enqueue_rss_analysis(db)
        db.commit()
        assert len(jobs) == RSS["daily_analysis_budget"] + 1
        assert (
            db.scalar(select(func.count()).select_from(RssDailyUsage))
            == 2 * RSS["daily_analysis_budget"] + 1
        )
        state = analysis_budget(db)
        assert not state["limits_enforced"] and state["unlimited"]
        assert (
            state["daily_limit"] is None
            and state["daily_remaining"] is None
            and state["remaining"] is None
        )
        assert not state["periodic_enabled"]
        assert all(not b["enforced"] for b in budget_status(db)["budgets"])


def test_old_exhausted_expired_grant_does_not_block_http_and_counters_are_kept(
    monkeypatch,
):
    monkeypatch.setattr(settings, "jev_budget_limits_enabled", False)
    monkeypatch.setattr(
        settings, "typesafe_api_key", SecretStr("MOCK-KEY-FOR-TRANSPORT")
    )
    original_client = httpx.Client
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=answer(calls[-1], linked=()))

    def client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return original_client(**kwargs)

    monkeypatch.setattr("app.jev.httpx.Client", client)
    with Session() as db:
        a = synthetic(db)
        budget = ConsumptionBudget(
            id="MOCK-EXPIRED",
            request_limit=1,
            requests_used=200,
            started_at=now() - timedelta(days=30),
            window_seconds=1,
        )
        db.add(budget)
        db.flush()
        grant = Grant(
            id="MOCK-EXPIRED",
            split="training",
            article_limit=1,
            used=1,
            expires_at=now() - timedelta(days=30),
            budget_id=budget.id,
        )
        db.add(grant)
        db.flush()
        db.add(GrantArticle(article_id=a.id, grant_id=grant.id))
        db.commit()
        assert budget_available(db, budget.id)
        payload = stage_a(a.data, [s.data for s in db.scalars(select(Supplier))])
        result = JevClient(db, a.id).ask(payload, "a", time.monotonic() + 60)
        assert result["model"] == settings.jev_model and len(calls) == 1
        assert budget.requests_used == 201 and grant.used == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(ApiCall)
                .where(ApiCall.budget_id == budget.id)
            )
            == 1
        )
