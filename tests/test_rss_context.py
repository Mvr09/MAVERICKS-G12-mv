"""Casos sintéticos independientes; mocks identificados, sin etiquetas retenidas."""

import json
from datetime import timedelta
from io import BytesIO

import httpx
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select

from app.analysis import process_article
from app.db import Session
from app.enrichment import enrich, EditorialParser
from app.importer import import_excel
from app.main import app
from app.models import Article, Batch, Supplier, now
from app.rss_questions import stage_a, stage_b, VERSION
from app.settings import settings
from app.views import suppliers_view
from tests.helpers import synthetic, answer


def rss_article(db):
    a = synthetic(
        db, "MOCK: sea freight rates", "MOCK: prices rise ahead of new tariffs."
    )
    a.context = "rss"
    a.batch_id = None
    a.source_id = "the_loadstar"
    a.data = {
        **a.data,
        "context_id": "rss",
        "url": "https://theloadstar.com/mock-public-story/",
    }
    db.commit()
    return a


def test_enrichment_public_text_provenance_cache_and_no_labels():
    calls = []
    body = (
        "MOCK IDENTIFICADO: Sea freight sailings cancelled; delivery delays of 8 days. "
        * 5
    )

    def fetch(r):
        calls.append(str(r.url))
        assert "authorization" not in r.headers and "cookie" not in r.headers
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="User-agent: *\nAllow: /"
            if r.url.path == "/robots.txt"
            else f"<nav>irrelevant</nav><article><p>{body}</p><script>bad()</script></article>",
        )

    with Session() as db:
        a = rss_article(db)
        a.data = {**a.data, "Is_Risk": "PROTECTED", "Explanation": "PROTECTED"}
        enrich(db, a, httpx.MockTransport(fetch), check_dns=False)
        db.commit()
        assert a.data["enrichment"]["status"] == "public_text"
        assert body.strip() in a.data["full_text"]
        assert "irrelevant" not in a.data["full_text"]
        assert a.data["enrichment"]["text_hash"]
        enrich(db, a, httpx.MockTransport(fetch), check_dns=False)
        assert len(calls) == 2
        suppliers = [s.data for s in db.scalars(select(Supplier))]
        pa = stage_a(a.data, suppliers, settings.jev_model)
        pb = stage_b(a.data, suppliers[:1], [], settings.jev_model)
        assert "PROTECTED" not in json.dumps([pa, pb])
        assert len([q for q in pa["questions"] if q.startswith("identity_")]) == 40
        assert len([q for q in pa["questions"] if q.startswith("exposure_")]) == 40
        assert any(e["field"] == "full_text" for e in pb["state"]["evidence_spans"])
        assert (
            "route and transport mode must match"
            in pa["questions"]["exposure_S033"]["instructions"]
        )


def test_enrichment_blocks_redirects_robots_and_paywall():
    for mode in ("redirect", "robots", "paywall", "oversize", "unavailable"):
        calls = []

        def fetch(r):
            calls.append(str(r.url))
            if r.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nDisallow: /"
                    if mode == "robots"
                    else "User-agent: *\nAllow: /",
                )
            if mode == "redirect":
                return httpx.Response(
                    302, headers={"location": "https://127.0.0.1/private"}
                )
            if mode == "oversize":
                return httpx.Response(
                    200, headers={"content-type": "text/html"}, content=b"x" * 2_000_001
                )
            if mode == "unavailable":
                return httpx.Response(403)
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text='<script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false,"articleBody":"secret"}</script><article><p>'
                + "restricted content " * 50
                + "</p></article>",
            )

        with Session() as db:
            a = rss_article(db)
            enrich(db, a, httpx.MockTransport(fetch), check_dns=False)
            assert a.data["enrichment"]["status"] == "summary_only"
            assert not a.data["full_text"]
            assert not any("127.0.0.1" in url for url in calls)


def evaluate(db, a, risk, linked=("S032",), low_metadata=True):
    def fetch(r):
        payload = json.loads(r.content)
        result = answer(
            payload,
            linked=linked,
            risk=risk,
            urgent=0.02,
            event="other",
            impact="unclear" if risk < 0.35 else "active",
        )
        for key, value in result["answers"].items():
            if key.startswith(("identity_", "exposure_")):
                sid = key.rsplit("_", 1)[-1]
                value["noul"] = (
                    0.98 if key.startswith("exposure_") and sid in linked else 0.02
                )
            if low_metadata and key in ("event_type", "event_state"):
                value["confidence"] = 0.4
            if low_metadata and key.startswith(
                ("severity_", "impact_state_", "evidence_")
            ):
                value["confidence"] = 0.4
        return httpx.Response(200, json=result)

    return process_article(db, a.id, httpx.MockTransport(fetch), run_key="mock:" + a.id)


def test_rss_negative_metadata_notes_not_decision_review_but_risk_stays_strict():
    with Session() as db:
        a = rss_article(db)
        negative = evaluate(db, a, 0.02)
        assert negative["question_version"] == VERSION
        assert negative["analysis_status"] == "done"
        assert negative["is_risk"] == negative["urgent"] == "N"
        assert "severity_confidence_low" in negative["context_notes"]
        assert negative["affected_supplier_ids"] == ["S032"]
        assert "S033" not in negative["affected_supplier_ids"]
        b = rss_article(db)
        risky = evaluate(db, b, 0.98)
        assert risky["is_risk"] == "Y" and risky["analysis_status"] == "review"
        assert risky["assessments"][0]["needs_review"]
        c = rss_article(db)
        c.data = {**c.data, "summary": "MOCK: prices rise ..."}
        db.commit()
        incomplete = evaluate(db, c, 0.02)
        assert incomplete["analysis_status"] == "review"
        assert "source_text_incomplete" in incomplete["review_reasons"]


def test_full_text_evidence_is_verbatim_and_exercise_stays_frozen():
    with Session() as db:
        a = rss_article(db)
        a.data = {
            **a.data,
            "full_text": "MOCK: eight days of delays on the sea route.",
            "enrichment": {"status": "public_text", "checked_at": now().isoformat()},
        }
        db.commit()

        def fetch(r):
            payload = json.loads(r.content)
            result = answer(payload, linked=("S032",), urgent=0.02)
            for k, v in result["answers"].items():
                if k.startswith("evidence_"):
                    v["choice"] = "e3"
                    v["probabilities"] = {
                        x: float(x == "e3") for x in v["probabilities"]
                    }
            return httpx.Response(200, json=result)

        result = process_article(db, a.id, httpx.MockTransport(fetch))
        chosen = next(e for e in result["evidence"] if e["id"] == "e3")
        assert chosen["field"] == "full_text"
        assert (
            a.data[chosen["field"]][chosen["start"] : chosen["end"]] == chosen["text"]
        )
        exercise = synthetic(db)
        result = evaluate(db, exercise, 0.02, linked=("S001",))
        assert result["question_version"] == "1.0.0"
        assert result["analysis_status"] == "review"  # política anterior intacta
        assert "context_notes" not in result


def test_liveday_import_analysis_and_summary_origin_are_isolated(monkeypatch):
    monkeypatch.setattr(settings, "jev_budget_limits_enabled", False)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "News_Feed"
    sheet.append(["News_ID", "Published_Date", "Source", "Headline", "Summary"])
    sheet.append(
        [
            "MOCK-LIVE",
            "2026-10-06",
            "MOCK RSS publisher",
            "MOCK LiveDay",
            "MOCK fire stops production.",
        ]
    )
    stream = BytesIO()
    workbook.save(stream)
    with Session() as db:
        b, result = import_excel(db, stream.getvalue(), "demo_live.xlsx")
        db.commit()
        aid = db.scalar(select(Article.id).where(Article.batch_id == b.id))
        evaluated = process_article(
            db,
            aid,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), linked=("S001",))
                )
            ),
        )
        assert evaluated["analysis_status"] == "done"
        bid = b.id
        other = synthetic(db)
        process_article(
            db,
            other.id,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), linked=("S002",))
                )
            ),
        )
        ranking = suppliers_view(db, "exercise", "batch:" + bid)
        assert (
            next(s for s in ranking if s["supplier_id"] == "S001")["incident_count"]
            == 1
        )
        assert (
            next(s for s in ranking if s["supplier_id"] == "S002")["incident_count"]
            == 0
        )
    with TestClient(app) as c:
        query = "?context=exercise&origin=batch:" + bid
        overview = c.get("/api/overview" + query).json()
        assert overview["received"] == overview["processed"] == 1
        assert overview["active_incidents"] == 1
        rows = c.get("/api/articles" + query).json()
        assert len(rows) == 1 and rows[0]["split"] == "liveday"
        assert rows[0]["origin_label"] == "demo_live.xlsx"
        assert (
            next(b for b in c.get("/api/batches").json() if b["id"] == bid)["done"] == 1
        )


def test_origin_projection_uses_selected_severity_and_preserves_global_recovery():
    from app.models import Incident

    with Session() as db:
        first = synthetic(db)
        original = process_article(
            db,
            first.id,
            httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=answer(json.loads(r.content), linked=("S001",))
                )
            ),
        )
        second = synthetic(db, published="2026-10-02T12:00:00+00:00")

        def fetch(r):
            p = json.loads(r.content)
            result = answer(p, linked=("S001",), urgent=0.02)
            if "severity_S001" in result["answers"]:
                result["answers"]["severity_S001"]["score"] = 2
            return httpx.Response(200, json=result)

        process_article(db, second.id, httpx.MockTransport(fetch))
        incident = db.scalar(select(Incident).where(Incident.supplier_id == "S001"))
        assert len(incident.history) == 2
        filtered = next(
            s
            for s in suppliers_view(db, "exercise", "batch:" + first.batch_id)
            if s["supplier_id"] == "S001"
        )
        assert filtered["priority"] == original["assessments"][0]["priority"]
        assert filtered["priority"] != incident.priority
        assert len(filtered["incidents"][0]["history"]) == 1
        incident.state = "resolved"
        incident.priority = 0
        db.commit()
        recovered = next(
            s
            for s in suppliers_view(db, "exercise", "batch:" + first.batch_id)
            if s["supplier_id"] == "S001"
        )
        assert recovered["priority"] == 0 and recovered["incident_count"] == 0
