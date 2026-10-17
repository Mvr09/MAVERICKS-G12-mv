"""One explicit diagnosed retry per failed validation article, within existing limits."""

import json
from pathlib import Path
import time
import httpx
from app.settings import settings

BASE = "https://mavericks-g12-mv-production.up.railway.app"
state = json.loads(Path("reports/private/final-rehearsal.json").read_text())
bid = state["phases"]["validation"]["batch_id"]
budget = "demo-final-200-20261017"
report = {"batch_id": bid, "results": []}
with httpx.Client(base_url=BASE, headers={"Origin": BASE}, timeout=25) as c:
    worker = c.get("/api/worker").json()
    if not worker.get("compatible"):
        raise SystemExit("WORKER_VERSION_MISMATCH")
    login = c.post(
        "/api/session", json={"password": settings.admin_password.get_secret_value()}
    )
    if login.status_code != 200:
        raise SystemExit("AUTHENTICATION_FAILED")
    c.headers["X-CSRF-Token"] = login.json()["csrf"]
    try:
        rows = [
            a
            for a in c.get("/api/articles?context=exercise").json()
            if a.get("batch_id") == bid and a["state"] == "error"
        ]
        rows.sort(key=lambda a: a["analysis"]["error"] != "CONTRACT_SCORE")
        ack = c.post(
            f"/api/admin/budgets/{budget}/diagnose",
            json={
                "reason": "Contrato y SDK oficial ScoreAnswer contrastados: el campo score se valida por separado de probabilidades publicadas. Se retira la igualdad local adicional no documentada; se conservan tipos, rangos, distribución, modelo y diagnóstico. Sin cambios de preguntas, umbrales ni política."
            },
        )
        if ack.status_code != 200:
            raise SystemExit("DIAGNOSIS_FAILED")
        report["acknowledgement"] = ack.json()
        for a in rows:
            retried = c.post(
                "/api/articles/" + a["id"] + "/retry",
                json={
                    "reason": "Reintento aislado tras diagnóstico del SDK oficial ScoreAnswer y corrección del validador local; conserva presupuesto e intentos y el score del proveedor sin recalcularlo."
                },
            )
            if retried.status_code != 202:
                raise SystemExit("RETRY_REJECTED")
            jid = retried.json()["job_id"]
            deadline = time.monotonic() + 90
            while True:
                job = c.get("/api/jobs/" + jid).json()
                if job["state"] in ("done", "error"):
                    break
                if time.monotonic() >= deadline:
                    raise SystemExit("RETRY_MONITOR_TIMEOUT")
                time.sleep(1)
            report["results"].append(job)
            print(
                json.dumps(
                    {
                        "state": job["state"],
                        "error": job["error"],
                        "job_attempts": job["attempts"],
                    }
                ),
                flush=True,
            )
            if job["state"] == "error":
                break
        execution = c.get(f"/api/batches/{bid}/execution").json()
        report["execution"] = execution
        report["budgets"] = c.get("/api/admin/budgets").json()
        Path("reports/private/diagnosed-retry.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "contract_diagnostics": [
                        call["contract_diagnostic"]
                        for call in execution["calls"]
                        if call.get("contract_diagnostic")
                    ],
                    "budgets": report["budgets"]["budgets"],
                }
            ),
            flush=True,
        )
    finally:
        c.delete("/api/session")
