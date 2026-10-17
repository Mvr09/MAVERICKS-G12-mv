"""Start/restart the real worker with paid RSS inference disabled."""

import os, sys, subprocess, time, json
from sqlalchemy import select, func
from app.db import Session
from app.models import Job, ApiCall, Article, now
from app.queue import enqueue_sync
from app.settings import settings, ROOT

assert not settings.rss_analysis_enabled, (
    "Este ensayo exige análisis RSS de pago desactivado"
)
with Session() as db:
    before = db.scalar(select(func.count()).select_from(ApiCall))
    jobs = enqueue_sync(db, manual=True)
    db.commit()
env = dict(os.environ)
env["RSS_ANALYSIS_ENABLED"] = "false"


def start():
    return subprocess.Popen(
        [sys.executable, "-m", "app.worker"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop(proc):
    proc.terminate()
    proc.wait(timeout=10)


proc = start()
started = time.monotonic()
try:
    while time.monotonic() - started < 35:
        with Session() as db:
            states = [db.get(Job, j).state for j in jobs]
            if all(s in ("done", "error") for s in states):
                break
        time.sleep(0.2)
    else:
        raise RuntimeError("Worker no completó las consultas en el tiempo del ensayo")
    stop(proc)
    proc = start()
    time.sleep(1)
    with Session() as db:
        after = db.scalar(select(func.count()).select_from(ApiCall))
        assert before == after
        assert all(db.get(Job, j).state in ("done", "error") for j in jobs)
        report = {
            "environment": "local; not Railway",
            "checked_at": now().isoformat(),
            "worker_restart": True,
            "jobs": states,
            "seconds": round(time.monotonic() - started, 3),
            "jev_requests_before": before,
            "jev_requests_after": after,
            "rss_paid_analysis": False,
        }
        (ROOT / "reports/worker-local.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
finally:
    stop(proc)
