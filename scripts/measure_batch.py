"""Authorized final measurement, from enqueue through export readiness.
Uses existing backend credentials in memory. No automatic grant creation.
"""

import argparse, json, time
from pathlib import Path
import httpx
from app.settings import settings

p = argparse.ArgumentParser()
p.add_argument("url")
p.add_argument("batch_id")
p.add_argument("--output", default=".runtime/resultados.xlsx")
a = p.parse_args()
with httpx.Client(base_url=a.url.rstrip("/"), timeout=20, follow_redirects=False) as c:
    login = c.post(
        "/api/session", json={"password": settings.admin_password.get_secret_value()}
    )
    if login.status_code != 200:
        raise SystemExit("No se pudo autenticar al presentador")
    headers = {"x-csrf-token": login.json()["csrf"]}
    started = time.monotonic()
    r = c.post("/api/batches/" + a.batch_id + "/analyze", headers=headers)
    if r.status_code != 202:
        raise SystemExit("No se pudo encolar: revisa autorización y presupuesto")
    while time.monotonic() - started < 360:
        export = c.get("/api/batches/" + a.batch_id + "/export.xlsx")
        if export.status_code == 200:
            elapsed = time.monotonic() - started
            output = Path(a.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(export.content)
            print(
                json.dumps(
                    {
                        "elapsed_seconds": round(elapsed, 3),
                        "within_300_seconds": elapsed <= 300,
                        "export": str(output),
                        "environment": a.url,
                    }
                )
            )
            break
        if export.status_code != 409:
            raise SystemExit("Falló la comprobación de exportación")
        time.sleep(1)
    else:
        raise SystemExit("No se completó en 360 segundos; no cumple A20")
    c.delete("/api/session", headers=headers)
