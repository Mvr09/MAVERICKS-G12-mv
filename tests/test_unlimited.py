"""Autorización ilimitada con transporte sin red y conservación de límites técnicos."""

from datetime import timedelta
from sqlalchemy import select
from app.cli import seed
from app.db import Session
from app.models import Grant, ConsumptionBudget, GrantArticle, Article, now
from app.jev import reserve_request
from app.queue import reserve, budget_available
from app.main import analysis_budget, budget_status
from app.settings import RSS
from tests.helpers import synthetic


def test_unlimited_seed_no_expiry_preserves_accounting_and_bounded_history():
    with Session() as db:
        seed(db)
        db.commit()
        grant = db.get(Grant, "manual-unlimited-training-20261017")
        budget = db.get(ConsumptionBudget, grant.budget_id)
        budget.started_at = now() - timedelta(days=100)
        for _ in range(201):
            assert reserve_request(db, grant) == budget.id
        db.commit()
        seed(db)
        db.commit()
        assert budget.requests_used == 201 and budget_available(db, budget.id)
        assert grant.article_limit is None and grant.expires_at is None
        assert db.get(ConsumptionBudget, "demo-final-200-20261017").request_limit == 200
        assert db.get(Grant, "initial-training-3").article_limit == 3
        status = next(b for b in budget_status(db)["budgets"] if b["id"] == budget.id)
        assert status["unlimited"] and status["remaining_requests"] is None
        assert status["closes_at"] is None and status["requests_used"] == 201


def test_unlimited_rss_keeps_daily_cap_and_does_not_enable_automatic_analysis():
    with Session() as db:
        seed(db)
        # Remove only bounded grants in this isolated test so selection is explicit.
        for grant in db.scalars(select(Grant).where(Grant.split == "rss")):
            if grant.article_limit is not None:
                grant.used = grant.article_limit
        automatic = synthetic(db)
        automatic.context = "rss"
        assert not reserve(db, automatic, "rss")
        grant = db.get(Grant, "manual-unlimited-rss-20261017")
        for n in range(RSS["daily_analysis_budget"]):
            a = synthetic(db, headline=f"MOCK RSS daily {n}")
            a.context = "rss"
            assert reserve(db, a, "rss", manual_rss=True)
        blocked = synthetic(db, headline="MOCK RSS over daily cap")
        blocked.context = "rss"
        assert not reserve(db, blocked, "rss", manual_rss=True)
        assert grant.used == RSS["daily_analysis_budget"]
        state = analysis_budget(db)
        assert state["unlimited"] and state["remaining"] == 0
        assert state["daily_remaining"] == 0 and not state["periodic_enabled"]
