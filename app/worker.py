import time, threading, logging, os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, or_, text
from app.db import Session
from app.models import Job, Article, WorkerPresence, Comparison, now
from app.queue import claim, enqueue_sync, enqueue, reserve, analysis_key
from app.settings import settings, RSS

log = logging.getLogger("radar.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def pulse(worker_id):
    with Session() as db:
        db.merge(
            WorkerPresence(
                id=worker_id,
                heartbeat=now(),
                revision=os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "local",
            )
        )
        db.commit()


def heartbeat(jid, stop):
    while not stop.wait(10):
        with Session() as db:
            j = db.get(Job, jid)
            if not j or j.state != "running":
                return
            j.heartbeat = now()
            j.lease_until = now() + timedelta(seconds=90)
            db.commit()


def run_job(jid):
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(jid, stop), daemon=True)
    thread.start()
    try:
        with Session() as db:
            j = db.get(Job, jid)
            if j.kind == "analysis":
                from app.analysis import process_article

                article = db.get(Article, j.payload["article_id"])
                if article and (
                    article.state == "superseded"
                    or article.generation != j.payload.get("generation", 0)
                ):
                    j.state = "done"
                    j.error = None
                    j.lease_until = None
                    db.commit()
                    return
                from app.profiles import CANDIDATE_PROFILE
                from app.profiles import candidate_versions
                if j.payload.get("analysis_profile") == CANDIDATE_PROFILE and j.payload.get("analysis_versions") != candidate_versions():
                    j.state = "error"
                    j.error = "PROFILE_VERSION_CHANGED"
                    j.lease_until = None
                    article.state = "error"
                    db.commit()
                    return
                snapshot = j.payload.get("profile_snapshot")
                if snapshot:
                    from app.profiles import profile_snapshot
                    if snapshot != profile_snapshot(j.payload.get("analysis_profile", "1.0.0"), article.context):
                        j.state = "error"; j.error = "PROFILE_CONFIG_CHANGED"; article.state = "error"
                        j.lease_until = None; db.commit(); return
                j.payload = {**j.payload, "telemetry": {**j.payload.get("telemetry", {}), "started_at": j.payload.get("telemetry", {}).get("started_at") or now().isoformat(), "environment": "Railway" if os.environ.get("RAILWAY_GIT_COMMIT_SHA") else "local", "revision": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")}}
                db.commit()
                r = process_article(
                    db,
                    j.payload["article_id"],
                    diagnostic_ack_at=j.payload.get("diagnostic_ack_at"),
                    profile=j.payload.get("analysis_profile", "1.0.0"),
                    profile_snapshot=snapshot,
                )
                j = db.get(Job, jid)
                j.state = "error" if r["analysis_status"] == "error" else "done"
                j.error = r["error"]
                from app.models import Analysis, ApiCall
                from app.queue import analysis_key
                generation=j.payload.get("generation",0)
                result_row=db.scalar(select(Analysis).where(Analysis.article_id==article.id,Analysis.generation==generation).order_by(Analysis.created_at.desc()))
                calls=db.scalars(select(ApiCall).where(ApiCall.article_id==article.id,ApiCall.run_key==(f"{article.id}:generation:{generation}" if generation else ""))).all()
                j.payload = {**j.payload, "telemetry": {**j.payload.get("telemetry", {}), "completed_at": now().isoformat(),
                    "queued_at":j.payload.get("queued_at"),"new_requests":len(calls),
                    "cached_stages":result_row.raw.get("_cache_stages",[]) if result_row else [],
                    "usage":{k:sum(c.usage.get(k,0) for c in calls) if calls and all(isinstance(c.usage.get(k),(int,float)) for c in calls) else None for k in ("input_tokens","output_tokens","total_tokens")}}}
            elif j.kind == "campaign":
                from app.campaigns import process
                result = process(db, j.payload["run_id"])
                j = db.get(Job, jid)
                j.state = "done" if result.state in ("done", "review") else "error" if result.state == "error" else "cancelled"
                j.error = (result.result or {}).get("error")
            elif j.kind == "comparison":
                from app.comparison import process_comparison

                article = db.get(Article, j.payload["article_id"])
                comparison = db.get(Comparison, j.payload["comparison_id"])
                if article.generation != j.payload.get("generation", 0):
                    comparison.state = "cancelled"
                    j.state = "cancelled"
                else:
                    result = process_comparison(db, comparison.id)
                    j.state = result.state
                    j.error = (
                        "COMPARISON_REQUIRES_DIAGNOSIS"
                        if result.state == "error"
                        else None
                    )
            elif j.kind == "rss":
                from app.rss import sync_source

                result = sync_source(db, j.payload["source_id"])
                j.state = "error" if "error" in result else "done"
                j.error = result.get("error")
            else:
                j.state = "error"
                j.error = "UNKNOWN_JOB"
            j.lease_until = None
            db.commit()
    except Exception:
        # Never log provider response bodies, credentials or environment.
        with Session() as db:
            j = db.get(Job, jid)
            j.state = "error"
            j.error = "WORKER_INTERNAL_ERROR"
            if j.kind == "campaign":
                from app.campaigns import fail_run
                fail_run(db,j.payload.get("run_id"),"WORKER_INTERNAL_ERROR")
            if j.kind == "comparison":
                comparison = db.get(Comparison, j.payload.get("comparison_id"))
                if comparison:
                    comparison.state = "error"
                    comparison.summary = {
                        **comparison.summary,
                        "message": "Fallo interno del worker; requiere diagnóstico.",
                    }
            j.lease_until = None
            db.commit()
        log.error("job=%s status=WORKER_INTERNAL_ERROR", jid)
    finally:
        stop.set()
        thread.join(timeout=1)


def main():
    while True:
        try:
            with Session() as db:
                revision = db.execute(
                    text("select version_num from alembic_version")
                ).scalar_one()
                if revision == "0010":
                    break
        except Exception:
            pass
        log.info("Esperando esquema requerido")
        time.sleep(3)
    from app.cli import seed

    with Session() as db:
        seed(db)
        db.commit()
    worker_id = str(uuid4())
    last_pulse = 0
    futures = []
    last_sync = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        while True:
            try:
                if time.monotonic() - last_pulse >= 5:
                    pulse(worker_id)
                    last_pulse = time.monotonic()
                if time.monotonic() - last_sync >= RSS["poll_seconds"]:
                    with Session() as db:
                        enqueue_sync(db)
                        if settings.rss_analysis_enabled:
                            pending = db.scalars(
                                select(Article)
                                .where(
                                    Article.context == "rss", Article.state == "pending"
                                )
                                .order_by(Article.fetched_at)
                            ).all()
                            for a in pending:
                                if reserve(db, a, "rss"):
                                    enqueue(
                                        db,
                                        analysis_key(a),
                                        "analysis",
                                        {
                                            "article_id": a.id,
                                            "generation": a.generation,
                                        },
                                        1,
                                    )
                        db.commit()
                    last_sync = time.monotonic()
                futures = [f for f in futures if not f.done()]
                while len(futures) < 4:
                    with Session() as db:
                        j = claim(db)
                        db.commit()
                    if not j:
                        break
                    futures.append(executor.submit(run_job, j.id))
            except Exception:
                log.error("Fallo temporal de cola; reintento del sondeo")
            time.sleep(0.5)


if __name__ == "__main__":
    main()
