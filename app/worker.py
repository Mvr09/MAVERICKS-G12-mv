import time, threading, logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from sqlalchemy import select, or_, text
from app.db import Session
from app.models import Job, Article, now
from app.queue import claim, enqueue_sync, enqueue, reserve
from app.settings import settings, RSS

log = logging.getLogger("radar.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


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
                if article and article.state == "superseded":
                    j.state = "done"
                    j.error = None
                    j.lease_until = None
                    db.commit()
                    return
                r = process_article(
                    db,
                    j.payload["article_id"],
                    diagnostic_ack_at=j.payload.get("diagnostic_ack_at"),
                )
                j = db.get(Job, jid)
                j.state = "error" if r["analysis_status"] == "error" else "done"
                j.error = r["error"]
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
                if revision == "0002":
                    break
        except Exception:
            pass
        log.info("Esperando esquema requerido")
        time.sleep(3)
    futures = []
    last_sync = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        while True:
            try:
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
                                .limit(RSS["daily_analysis_budget"])
                            ).all()
                            for a in pending:
                                if reserve(db, a, "rss"):
                                    enqueue(
                                        db,
                                        "analysis:" + a.id,
                                        "analysis",
                                        {"article_id": a.id},
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
