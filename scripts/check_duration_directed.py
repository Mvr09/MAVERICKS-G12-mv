"""Resumable six-case check; no network unless --execute is explicit.

Dedicated local database only. No Excel import, production changes or tuning.
"""
import argparse
import hashlib
import json
import time

from sqlalchemy import select, func
from sqlalchemy.engine import make_url

from app.analysis import SCHEMA
from app.db import Session, engine
from app.duration import durations, VERSION as DURATION_VERSION
from app.importer import digest
from app.jev import JevClient, ProviderError
from app.link_analysis import normalize
from app.link_questions import stage_a, stage_b, select_candidates, VERSION
from app.models import Article, Batch, Supplier, Grant, GrantArticle, ConsumptionBudget, ApiCall
from app.schemas import NormalizedAnalysis
from app.settings import ROOT, settings
from jsonschema import validate

BUDGET = "duration-directed-20261018-v1"
RUN_KEY = "duration-directed:duration-1.1.0:link-2.2.0"
REPORT = ROOT / "reports/private/duration-directed-results.json"
FILES = ["reports/duration-directed-check.json", "app/duration.py", "app/analysis.py",
         "app/jev.py", "app/link_questions.py", "app/link_analysis.py",
         "app/geography.py", "config/geography.json", "config/risk_policy.json",
         "reference/jev_requests.py"]


def write(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "reports/duration-directed-check.json").read_text())
    assert plan["profile"] == VERSION and plan["extractor"] == DURATION_VERSION
    assert plan["model"] == settings.jev_model
    assert len(plan["cases"]) == 6 and plan["maximum_requests_including_retries"] == 36
    hashes = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}
    for f, h in json.loads((ROOT / "reports/link-v2-freeze.json").read_text())["files"].items():
        assert hashes.get(f, hashlib.sha256((ROOT / f).read_bytes()).hexdigest()) == h, f
    if not args.execute:
        print(json.dumps({"prepared_cases": 6, "maximum_requests": 36, "executed": False}))
        return
    if make_url(str(engine.url)).database != "radar_link_development":
        raise SystemExit("Dedicated database radar_link_development required")
    settings.jev_budget_limits_enabled = True
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {
        "profile": VERSION, "model": settings.jev_model, "extractor": DURATION_VERSION,
        "maximum_requests": 36, "files": hashes, "results": {}, "errors": [],
    }
    assert report["files"] == hashes, "Frozen inputs changed; do not rerun"
    with Session() as db:
        suppliers = [s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
        assert len(suppliers) == 40
        catalog_hash = digest(suppliers)
        assert report.get("catalog_hash", catalog_hash) == catalog_hash
        report["catalog_hash"] = catalog_hash
        report.setdefault("global_calls_before", db.scalar(select(func.count()).select_from(ApiCall)))
        budget = db.get(ConsumptionBudget, BUDGET)
        if not budget:
            budget = ConsumptionBudget(id=BUDGET, request_limit=36)
            db.add(budget)
        else:
            assert budget.request_limit == 36
        if not db.get(Grant, BUDGET):
            db.add(Grant(id=BUDGET, split="training", article_limit=6, used=0, budget_id=BUDGET))
        batch_hash = digest({"duration_plan": plan, "files": hashes, "catalog": catalog_hash})
        batch = db.scalar(select(Batch).where(Batch.file_hash == batch_hash))
        if not batch:
            batch = Batch(file_hash=batch_hash, filename="SINTETICOS_DURACION_QA", split="training", count=6)
            db.add(batch)
            db.flush()
            for i, case in enumerate(plan["cases"]):
                data = case["article"]
                db.add(Article(origin_key=BUDGET + ":" + case["case"], batch_id=batch.id,
                    context="exercise", row_order=i, news_id=data["news_id"], data=data,
                    content_hash=digest(data)))
            db.flush()
        articles = db.scalars(select(Article).where(Article.batch_id == batch.id).order_by(Article.row_order)).all()
        assert len(articles) == 6
        for article, case in zip(articles, plan["cases"]):
            assert article.data == case["article"]
            if not db.get(GrantArticle, article.id):
                db.add(GrantArticle(article_id=article.id, grant_id=BUDGET))
                db.get(Grant, BUDGET).used += 1
        db.commit()
        write(report)
        started = time.monotonic()
        calls_at_start = db.scalar(select(func.count()).select_from(ApiCall).where(ApiCall.budget_id == BUDGET))
        reused_cases = len(report["results"])
        if "invocation_seconds" in report and "invocations" not in report:
            report["invocations"] = [{"seconds": report["invocation_seconds"], "new_requests": report["requests"], "reused_completed_cases": 0}]
        try:
            for article, case in zip(articles, plan["cases"]):
                if case["case"] in report["results"]:
                    continue
                candidates = durations(article.data)
                assert candidates == [{"id": "d1", **case["expected_candidate"]}]
                client = JevClient(db, article.id, run_key=RUN_KEY)
                deadline = time.monotonic() + 60
                a = client.ask(stage_a(article.data, suppliers, settings.jev_model), "a", deadline)
                selected = select_candidates(article.data, suppliers, a)
                b = client.ask(stage_b(article.data, selected, candidates, settings.jev_model), "b", deadline) if selected else None
                result = normalize(article, suppliers, a, b, candidates)
                NormalizedAnalysis.model_validate(result)
                validate(result, SCHEMA)
                target = next((s for s in result["assessments"] if s["supplier_id"] == "S024"), None)
                answer = (b or {}).get("answers", {}).get("duration_S024", {})
                span = case["expected_candidate"]["text"]
                checks = {
                    "duration_selected": answer.get("choice") == "d1",
                    "days": bool(target and target["duration_days"] == 2.),
                    "literal_span": any(span in article.data.get(f, "") for f in ("headline", "summary")),
                    "bound": bool(target and target["duration_is_lower_bound"] == case["expected_candidate"]["lower_bound"]),
                    "candidate_matches_source": candidates[0]["text"] == span,
                }
                report["results"][case["case"]] = {"article_id": article.id, "expected": case["expected_candidate"],
                    "candidates": candidates, "checks": checks, "passed": all(checks.values()),
                    "raw_a": a, "raw_b": b, "prediction": result,
                    "cached_stages": client.cached_stages, "new_requests": client.network_requests}
                write(report)
                print(json.dumps({"case": case["case"], "passed": all(checks.values()),
                    "selected": answer.get("choice"), "duration_days": target["duration_days"] if target else None,
                    "lower_bound": target["duration_is_lower_bound"] if target else None,
                    "risk": result["is_risk"], "urgent": result["urgent"], "status": result["analysis_status"]}), flush=True)
        except ProviderError as exc:
            report["errors"].append({"code": exc.code})
            print(json.dumps({"stopped": True, "code": exc.code}), flush=True)
        finally:
            calls = db.scalars(select(ApiCall).where(ApiCall.budget_id == BUDGET).order_by(ApiCall.created_at)).all()
            report["requests"] = len(calls)
            report["reserved_requests"] = db.get(ConsumptionBudget, BUDGET).requests_used
            report["global_calls_after"] = db.scalar(select(func.count()).select_from(ApiCall))
            report["invocation_seconds"] = time.monotonic() - started
            report.setdefault("invocations", []).append({"seconds": report["invocation_seconds"],
                "new_requests": len(calls) - calls_at_start, "reused_completed_cases": reused_cases})
            report["calls"] = [{"stage": c.stage, "article_id": c.article_id, "attempt": c.attempt,
                "seconds": c.duration, "status": c.status, "model": c.model, "usage": c.usage} for c in calls]
            report["indefinite_offline"] = all(durations({"summary": t}) == [] for t in (
                "until further notice", "indefinitely", "por tiempo indefinido", "varios días"))
            report["passed"] = len(report["results"]) == 6 and all(r["passed"] for r in report["results"].values()) and report["indefinite_offline"] and not report["errors"]
            assert len(calls) <= 36 and report["reserved_requests"] <= 36
            write(report)
    print(json.dumps({"passed": report["passed"], "requests": report["requests"],
        "completed_cases": len(report["results"]), "indefinite_offline": report["indefinite_offline"]}), flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
