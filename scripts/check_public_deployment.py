"""Read-only HTTPS verification; no session, uploads or inference calls."""

import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument(
    "--url", default="https://mavericks-g12-mv-production.up.railway.app"
)
parser.add_argument("--expected-commit", default="")
parser.add_argument("--report", default="reports/public-deployment.json")
args = parser.parse_args()
base = args.url.rstrip("/")
if not base.startswith("https://"):
    parser.error("La comprobación pública requiere HTTPS")
report = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "url": base,
    "expected_commit": args.expected_commit,
    "requests": [],
    "success": False,
}
with httpx.Client(timeout=20, follow_redirects=False) as client:
    responses = {}
    for path in [
        "/",
        "/healthz",
        "/readyz",
        "/api/suppliers",
        "/api/sources",
        "/api/config",
    ]:
        row = {"path": path}
        try:
            response = client.get(base + path)
            responses[path] = response
            row.update(
                http=response.status_code,
                content_type=response.headers.get("content-type"),
            )
            try:
                data = response.json()
            except ValueError:
                data = {}
            if path == "/api/suppliers" and response.status_code == 200:
                row["supplier_count"] = data.get("total")
            elif (
                path == "/api/sources"
                and response.status_code == 200
                and isinstance(data, list)
            ):
                row["source_count"] = len(data)
            elif path == "/api/config" and response.status_code == 200:
                row["rss_paid_analysis"] = data.get("rss_paid_analysis")
            elif path in ("/healthz", "/readyz") and response.status_code == 200:
                row["status"] = data.get("status")
                row["revision"] = data.get("revision")
                row["schema"] = data.get("schema")
            elif response.status_code != 200:
                row["error"] = (
                    data.get("message", "Respuesta no satisfactoria")
                    if isinstance(data, dict)
                    else "Respuesta no satisfactoria"
                )
        except httpx.RequestError as exc:
            row["error"] = type(exc).__name__
        report["requests"].append(row)
    home = responses.get("/")
    if home is not None and home.status_code == 200:
        assets = sorted(set(re.findall(r'(?:src|href)="(/assets/[^\"]+)"', home.text)))
        for path in assets:
            response = client.get(base + path)
            report["requests"].append(
                {
                    "path": path,
                    "http": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "bytes": len(response.content),
                }
            )
        report["asset_count"] = len(assets)
    health = next(r for r in report["requests"] if r["path"] == "/healthz")
    report["revision_matches"] = bool(
        args.expected_commit and health.get("revision") == args.expected_commit
    )
    report["application_healthy"] = (
        all(r.get("http") == 200 for r in report["requests"])
        and report.get("asset_count", 0) > 0
        and health.get("status") == "ok"
        and all(
            "javascript" in (r.get("content_type") or "")
            or "text/css" in (r.get("content_type") or "")
            for r in report["requests"]
            if r["path"].startswith("/assets/")
        )
    )
    report["catalogue_ready"] = (
        next(r for r in report["requests"] if r["path"] == "/api/suppliers").get(
            "supplier_count"
        )
        == 40
    )
    observed_rss = next(
        r for r in report["requests"] if r["path"] == "/api/config"
    ).get("rss_paid_analysis")
    report["rss_paid_analysis_disabled"] = (
        None if observed_rss is None else observed_rss is False
    )
    report["success"] = (
        report["application_healthy"]
        and report["catalogue_ready"]
        and report["rss_paid_analysis_disabled"]
        and (not args.expected_commit or report["revision_matches"])
    )
path = Path(args.report)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["success"]:
    raise SystemExit(1)
