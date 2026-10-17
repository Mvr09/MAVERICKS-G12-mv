"""Public Railway smoke test and explicitly authorized, bounded RSS execution.

No original datasets, labels, credential values, session cookies or headers in reports.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx
from app.settings import settings

BASE = "https://mavericks-g12-mv-production.up.railway.app"
parser = argparse.ArgumentParser(
    description="Verificar RSS en Railway y el lote autorizado 10/60"
)
parser.add_argument(
    "--analyze",
    action="store_true",
    help="Ejecutar solo el cupo RSS previamente autorizado",
)
args = parser.parse_args()
path = Path("reports/rss-railway-execution.json")
report = json.loads(path.read_text()) if path.exists() else {"url": BASE}
report["checked_at"] = datetime.now(timezone.utc).isoformat()
report.pop("check_error", None)


def save():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def read(client, route):
    response = client.get(route)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP_{response.status_code}")
    return response.json()


try:
    with httpx.Client(base_url=BASE, headers={"Origin": BASE}, timeout=25) as client:
        report["revision"] = read(client, "/healthz").get("revision")
        report["worker"] = read(client, "/api/worker")
        report["sources"] = [
            {
                k: s.get(k)
                for k in (
                    "id",
                    "status",
                    "last_attempt_at",
                    "last_success_at",
                    "http_status",
                    "received_count",
                    "duplicates",
                    "error",
                    "job_state",
                )
            }
            for s in read(client, "/api/sources")
        ]
        config = read(client, "/api/config")
        report["periodic_paid_analysis"] = config["rss_paid_analysis"]
        if report["periodic_paid_analysis"]:
            raise RuntimeError("ANALISIS_PERIODICO_DEBE_ESTAR_DESACTIVADO")
        password = settings.admin_password.get_secret_value()
        if not password:
            raise RuntimeError("ADMIN_PASSWORD_FALTANTE")
        response = client.post("/api/session", json={"password": password})
        report["authentication_http"] = response.status_code
        if response.status_code != 200:
            raise RuntimeError(f"AUTH_HTTP_{response.status_code}")
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        try:
            budget = read(client, "/api/analysis/budget")
            report["budget_observed"] = budget
            if args.analyze and not report.get("job_ids") and budget["remaining"] > 0:
                if not report["worker"]["online"]:
                    raise RuntimeError("WORKER_SIN_CONEXION")
                report["budget_before"] = budget
                report["execution_started_at"] = datetime.now(timezone.utc).isoformat()
                save()
                response = client.post(
                    "/api/analysis/rss", json={"limit": min(10, budget["remaining"])}
                )
                report["enqueue_http"] = response.status_code
                if response.status_code != 202:
                    raise RuntimeError(f"ENQUEUE_HTTP_{response.status_code}")
                result = response.json()
                report["job_ids"] = result["job_ids"]
                report["articles_queued"] = result["articles"]
                report["maximum_requests"] = result["maximum_requests"]
                assert result["articles"] <= 10 and result["maximum_requests"] <= 60
                save()
                print(
                    json.dumps(
                        {
                            "queued": result["articles"],
                            "maximum_requests": result["maximum_requests"],
                        }
                    ),
                    flush=True,
                )
            deadline = time.monotonic() + 240
            while report.get("job_ids"):
                jobs = [read(client, "/api/jobs/" + jid) for jid in report["job_ids"]]
                report["jobs"] = jobs
                states = dict(Counter(j["state"] for j in jobs))
                report["job_states"] = states
                save()
                if all(j["state"] in ("done", "error") for j in jobs):
                    report.setdefault(
                        "execution_finished_at", datetime.now(timezone.utc).isoformat()
                    )
                    report["elapsed_seconds"] = round(
                        (
                            datetime.fromisoformat(report["execution_finished_at"])
                            - datetime.fromisoformat(report["execution_started_at"])
                        ).total_seconds(),
                        3,
                    )
                    break
                if time.monotonic() >= deadline:
                    report["monitor_timeout"] = True
                    break
                print(json.dumps({"states": states}), flush=True)
                time.sleep(3)
            articles = read(client, "/api/articles?context=rss")
            report["article_states"] = dict(Counter(a["state"] for a in articles))
            report["total_rss_articles"] = len(articles)
            report["processed_articles"] = [
                {
                    "id": a["id"],
                    "source": a["source"],
                    "state": a["state"],
                    "model": a["analysis"].get("model_id"),
                    "error": a["analysis"].get("error"),
                    "review_reasons": a["analysis"].get("review_reasons", []),
                    "is_risk": a["analysis"].get("is_risk"),
                    "urgent": a["analysis"].get("urgent"),
                    "affected_suppliers": a["analysis"].get("affected_supplier_ids"),
                    "new_requests": a.get("new_requests"),
                    "cached": a.get("cached"),
                    "cache_stages": a.get("cache_stages"),
                }
                for a in articles
                if a.get("analysis")
            ]
            report["budget_after"] = read(client, "/api/analysis/budget")
            if "budget_before" in report:
                report["new_network_requests"] = (
                    report["budget_after"]["network_requests"]
                    - report["budget_before"]["network_requests"]
                )
                report["within_authorized_limit"] = (
                    report["new_network_requests"] <= 60
                    and report.get("articles_queued", 0) <= 10
                )
            report["usage_evidence"] = (
                "Uso reportado por la API persistido en PostgreSQL api_calls.usage; no consultado por este endpoint."
            )
        finally:
            client.delete("/api/session")
    save()
    print(
        json.dumps(
            {
                k: report.get(k)
                for k in (
                    "revision",
                    "worker",
                    "total_rss_articles",
                    "article_states",
                    "job_states",
                    "elapsed_seconds",
                    "new_network_requests",
                    "budget_after",
                    "within_authorized_limit",
                )
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
except Exception as exc:
    # Never serialize request objects, headers or arbitrary exception messages.
    report["check_error"] = (
        str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
    )
    save()
    print(json.dumps({"check_error": report["check_error"]}), flush=True)
    raise SystemExit(1)
