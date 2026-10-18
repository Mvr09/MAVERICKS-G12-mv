"""Synthetic diagnostic regressions. No held-out examples or real API calls."""
import json
from copy import deepcopy
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.db import Session
from app.models import Analysis, ApiCall, EvaluationLabel, Batch
from app.analysis import process_article
from app.diagnostics import review_trace, diagnose_batch
from app.settings import POLICY
from tests.helpers import synthetic, answer
from tests.test_operations import login


def test_private_diagnostic_attributes_discarded_candidates_and_preserves_results():
    with Session() as db:
        a = synthetic(db, "MOCK discarded uncertain supplier")
        def fetch(r):
            payload = json.loads(r.content)
            out = answer(payload, linked=("S002",), risk=0.02, urgent=0.02, impact="unrelated")
            if "linked_S001" in out["answers"]:
                out["answers"]["linked_S001"]["noul"] = 0.42
            if "risk_S001" in out["answers"]:
                out["answers"]["risk_S001"]["noul"] = 0.98
            return httpx.Response(200, json=out)
        result = process_article(db, a.id, httpx.MockTransport(fetch))
        db.add(EvaluationLabel(article_id=a.id, data={"Is_Risk":"Y", "Urgent":"N", "Affected_Supplier_IDs":"S001", "Explanation":"PRIVATE MOCK REFERENCE"}))
        batch = db.get(Batch, a.batch_id)
        batch.split = "validation"
        bid, aid = batch.id, a.id
        db.commit()
        original = deepcopy(result)
        calls = db.scalar(select(func.count()).select_from(ApiCall))
        report = diagnose_batch(db, bid)
        assert report["summary"]["risk_false_negatives"] == 1
        assert report["summary"]["missing_supplier_associations"] == 1
        row = report["rows"][0]
        assert row["review"]["root_scopes"] == ["discarded_candidate"]
        assert row["missing_suppliers"] == ["S001"]
        assert row["supplier_gates"][0]["gate"] == "below_link_threshold"
        assert row["supplier_gates"][0]["stage_b_evaluated"]
        inherited = next(c for c in row["review"]["causes"] if c["supplier_id"] == "S002")
        assert inherited["scope"] == "inherited"
        assert inherited["details"]["inherited_from"] == ["link_ambiguous:S001"]
        assert db.scalar(select(Analysis.result).where(Analysis.article_id==aid)) == original
        assert db.scalar(select(func.count()).select_from(ApiCall)) == calls
    with TestClient(app) as c:
        assert c.get("/api/model/diagnostics/"+bid).status_code == 401
        assert "PRIVATE MOCK REFERENCE" not in c.get("/api/articles/"+aid).text
        login(c)
        response = c.get("/api/model/diagnostics/"+bid)
        assert response.status_code == 200
        assert "no-store" in response.headers["cache-control"]
        assert "PRIVATE MOCK REFERENCE" in response.text
        assert response.json()["thresholds"] == POLICY["thresholds"]


def test_auxiliary_global_review_is_not_fabricated_as_risk_ambiguity():
    with Session() as db:
        a = synthetic(db)
        def fetch(r):
            p=json.loads(r.content)
            out=answer(p, linked=("S001",), risk=0.02, urgent=0.02, impact="unrelated")
            if "event_type" in out["answers"]:
                out["answers"]["event_type"]["confidence"] = 0.2
            return httpx.Response(200,json=out)
        result=process_article(db,a.id,httpx.MockTransport(fetch))
        run=db.scalar(select(Analysis).where(Analysis.article_id==a.id))
        traced=review_trace(result,run.raw)
        assert traced["root_scopes"] == ["auxiliary"]
        assert traced["inherited"] == [{"supplier_id":"S001","from":["event_type_confidence_low"]}]
        assert all(c["details"].get("direct_causes",[]) == [] for c in traced["causes"] if c["origin"]=="assessment")


def test_risk_gate_omission_before_stage_b_and_auxiliary_negative_review():
    with Session() as db:
        a=synthetic(db)
        process_article(db,a.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=()))))
        db.add(EvaluationLabel(article_id=a.id,data={"Is_Risk":"Y","Urgent":"N","Affected_Supplier_IDs":"S001"}))
        db.commit()
        row=diagnose_batch(db,a.batch_id)["rows"][0]
        assert row["risk_false_negative"]
        assert row["supplier_gates"][0]["gate"]=="excluded_before_stage_b"
        assert not row["supplier_gates"][0]["stage_b_evaluated"]
        assert row["prediction"]["analysis_status"]=="done"
