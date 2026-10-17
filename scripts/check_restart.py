"""Exercise a real web process restart, retaining session and DB records in memory."""

import subprocess, sys, os, time, json
import httpx
from app.settings import settings


def start():
    env = dict(os.environ)
    env["APP_BASE_URL"] = "http://127.0.0.1:8002"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            if httpx.get("http://127.0.0.1:8002/readyz").status_code == 200:
                return proc
        except httpx.RequestError:
            pass
        time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("Web no arrancó")


def stop(proc):
    proc.terminate()
    proc.wait(timeout=10)


proc = start()
try:
    with httpx.Client(base_url="http://127.0.0.1:8002") as c:
        r = c.post(
            "/api/session",
            json={"password": settings.admin_password.get_secret_value()},
        )
        assert r.status_code == 200
        csrf = r.json()["csrf"]
        before = c.get("/api/overview").json()
        stop(proc)
        proc = start()
        assert c.get("/api/session").json()["presenter"] is True
        after = c.get("/api/overview").json()
        assert before["supplier_count"] == after["supplier_count"] == 40
        assert before["received"] == after["received"]
        assert before["processed"] == after["processed"]
        assert c.get("/proveedores/S001").status_code == 200
        assert (
            c.delete("/api/session", headers={"x-csrf-token": csrf}).status_code == 200
        )
        print(
            json.dumps(
                {
                    "restart": "passes",
                    "session_retained": True,
                    "suppliers": after["supplier_count"],
                    "articles": after["received"],
                    "analyses": after["processed"],
                    "deep_route": 200,
                }
            )
        )
finally:
    stop(proc)
