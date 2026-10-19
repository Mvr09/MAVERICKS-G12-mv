import io, json, os
from uuid import UUID
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db import get_db, DatabaseConfigurationError
from app.settings import settings, ROOT, POLICY, RSS
from app.rss_questions import VERSION as RSS_QUESTION_VERSION
from app.profiles import DEFAULT_PROFILE, PUBLIC_EXERCISE_PROFILES, LEGACY_PROFILE
from app.models import *
from app.auth import presenter, identity, login, codec
from app.importer import import_excel, export_batch, digest
from app.event_tags import event_tag
from app.views import (
    suppliers_view,
    articles_view,
    sources_view,
    article_view,
    batch_label,
)

app = FastAPI(title="Supplier Risk Radar", docs_url=None, redoc_url=None)


@app.middleware("http")
async def security(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def database_unavailable(code, message):
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "30"},
        content={
            "code": code,
            "message": message,
            "details": None,
            "retryable": code != "DATABASE_CONFIGURATION",
        },
    )


@app.exception_handler(DatabaseConfigurationError)
async def database_config_error(request, exc):
    return database_unavailable(
        "DATABASE_CONFIGURATION",
        "PostgreSQL remoto sin configurar. Requiere intervención del presentador.",
    )


@app.exception_handler(OperationalError)
async def database_connection_error(request, exc):
    # Provider messages and SQL parameters can contain credentials or private data.
    return database_unavailable(
        "DATABASE_UNAVAILABLE",
        "La base de datos no está disponible. Reintenta más tarde.",
    )


@app.exception_handler(ProgrammingError)
async def database_query_error(request, exc):
    if getattr(exc.orig, "sqlstate", None) in ("42P01", "42703", "3F000"):
        return database_unavailable(
            "DATABASE_SCHEMA_UNAVAILABLE",
            "El esquema de la base de datos requiere migraciones del presentador.",
        )
    return JSONResponse(
        status_code=500,
        content={
            "code": "DATABASE_QUERY_ERROR",
            "message": "No se pudo completar la consulta.",
            "details": None,
            "retryable": False,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "details": None,
            "retryable": exc.status_code in (429, 503),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION",
            "message": "Entrada inválida",
            "details": [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                for e in exc.errors()
            ],
            "retryable": False,
        },
    )


@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "revision": os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "local",
    }


@app.get("/readyz")
def ready(db: Session = Depends(get_db)):
    try:
        revision = db.execute(
            text("select version_num from alembic_version")
        ).scalar_one()
        if revision != "0010":
            raise ValueError()
    except Exception:
        raise HTTPException(503, "Base de datos o esquema no disponible")
    return {"status": "ok", "schema": revision}


class Login(BaseModel):
    password: str = Field(max_length=1024)


@app.post("/api/session")
def start_session(
    body: Login, request: Request, response: Response, db: Session = Depends(get_db)
):
    if request.headers.get("origin") and request.headers["origin"].rstrip(
        "/"
    ) != settings.app_base_url.rstrip("/"):
        raise HTTPException(403, "Origen no permitido")
    record = login(request, db, body.password)
    response.set_cookie(
        "radar_session",
        codec().dumps(record.id),
        httponly=True,
        secure=settings.app_base_url.startswith("https://"),
        samesite="lax",
        max_age=28800,
    )
    return {"presenter": True, "csrf": record.csrf}


@app.get("/api/session")
def session(request: Request, db: Session = Depends(get_db)):
    record = identity(request, db)
    return {"presenter": bool(record), "csrf": record.csrf if record else None}


@app.delete("/api/session")
def logout(
    response: Response, record=Depends(presenter), db: Session = Depends(get_db)
):
    db.delete(record)
    db.commit()
    response.delete_cookie("radar_session")
    return {"presenter": False}


@app.get("/api/config")
def config():
    from app.profiles import candidate_versions
    return {
        "candidate_versions": candidate_versions(),
        "model": settings.jev_model,
        "policy_version": POLICY["version"],
        "question_version": DEFAULT_PROFILE,
        "default_profile": DEFAULT_PROFILE,
        "default_components": __import__("app.profiles",fromlist=["profile_snapshot"]).profile_snapshot(DEFAULT_PROFILE),
        "rss_question_version": RSS_QUESTION_VERSION,
        "exercise_profiles": list(PUBLIC_EXERCISE_PROFILES),
        "engine_configured": bool(settings.typesafe_api_key.get_secret_value()),
        "bands": POLICY["bands"],
        "cooldown_seconds": POLICY["audio"]["cooldown_seconds"],
        "fixtures": settings.demo_fixtures_enabled,
        "rss_paid_analysis": settings.rss_analysis_enabled,
        "jev_budget_limits_enabled": settings.jev_budget_limits_enabled,
    }


@app.get("/api/admin/config", dependencies=[Depends(presenter)])
def admin_config():
    return settings.credential_status()


@app.get("/api/overview")
def overview(
    context: Literal["exercise", "rss"] = "exercise",
    origin: str = "",
    db: Session = Depends(get_db),
):
    suppliers = suppliers_view(db, context, origin)
    articles = articles_view(db, context, origin=origin)
    sources = sources_view(db)
    processed = [a for a in articles if a["state"] in ("done", "review")]
    from collections import Counter

    review_reasons = Counter()
    reading = Counter()
    for article in processed:
        result = article["analysis"]
        if article["state"] == "review":
            reasons = set(result["review_reasons"]) | {
                r
                for assessment in result["assessments"]
                for r in assessment["review_reasons"]
            }
            review_reasons.update(reasons)
        if context == "rss":
            reading.update(
                [(result.get("source_reading") or {}).get("status", "unrecorded")]
            )
    return {
        "review_rate": sum(a["state"] == "review" for a in processed) / len(processed)
        if processed
        else None,
        "automatic_rate": sum(a["state"] == "done" for a in processed) / len(processed)
        if processed
        else None,
        "review_reasons": [
            {"reason": k, "articles": v} for k, v in review_reasons.most_common()
        ],
        "reading_coverage": dict(reading),
        "supplier_count": len(suppliers),
        "urgent_suppliers": sum(s["urgent"] for s in suppliers),
        "active_incidents": sum(s["incident_count"] for s in suppliers),
        "received": len(articles),
        "processed": len(processed),
        "pending": sum(a["state"] == "pending" for a in articles),
        "errors": sum(a["state"] == "error" for a in articles),
        "review_model": sum(a["state"] == "review" for a in articles),
        "review": sum((a["state"] == "review" and (a.get("human_review") or {}).get("state") != "resolved") or (a.get("human_review") or {}).get("state") == "in_verification" for a in articles),
        "human_review_completed": sum((a.get("human_review") or {}).get("state") == "resolved" for a in articles),
        "linked": sum(
            bool(a["analysis"] and a["analysis"]["affected_supplier_ids"])
            for a in processed
        ),
        "risk": sum(a["analysis"]["is_risk"] == "Y" for a in processed),
        "urgent": sum(a["analysis"]["urgent"] == "Y" for a in processed),
        "healthy_sources": sum(s["status"] in ("ok", "unchanged") for s in sources),
        "source_count": len(sources),
        "sources": sources,
        "updated_at": now(),
        "context": context,
        "latencies": latencies(db, context, origin),
    }


def latencies(db, context, origin=""):
    eligible = (
        [a["id"] for a in articles_view(db, context, origin=origin)] if origin else None
    )
    values = sorted(
        db.scalars(
            select(Analysis.duration)
            .join(Article)
            .where(
                Article.context == context,
                Analysis.generation == Article.generation,
                Article.id.in_(eligible) if eligible is not None else True,
            )
        ).all()
    )
    return {
        "n": len(values),
        "p50": values[int((len(values) - 1) * 0.50)] if values else None,
        "p95": values[int((len(values) - 1) * 0.95)] if values else None,
    }


@app.get("/api/suppliers")
def suppliers(
    origin: str = "",
    context: Literal["exercise", "rss"] = "exercise",
    q: str = "",
    category: str = "",
    criticality: str = "",
    single_source: str = "",
    urgent: bool = False,
    alternate: str = "",
    product: str = "",
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
):
    rows = suppliers_view(db, context, origin)
    rows = [
        s
        for s in rows
        if (not q or q.casefold() in json.dumps(s, ensure_ascii=False).casefold())
        and (not category or s["category"] == category)
        and (not criticality or s["criticality"] == criticality)
        and (not single_source or s["single_source"] == single_source)
        and (not urgent or s["urgent"])
        and (not alternate or bool(s["alternate_id"]) == (alternate == "Y"))
        and (not product or product in s["products"])
    ]
    size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * size
    return {"items": rows[start : start + size], "total": len(rows)}


@app.get("/api/suppliers/{sid}")
def supplier(
    sid: str,
    context: Literal["exercise", "rss"] = "exercise",
    origin: str = "",
    db: Session = Depends(get_db),
):
    row = next(
        (s for s in suppliers_view(db, context, origin=origin) if s["supplier_id"] == sid), None
    )
    if not row:
        raise HTTPException(404, "Proveedor no encontrado")
    alt = db.get(Supplier, row["alternate_id"]) if row["alternate_id"] else None
    return {
        **row,
        "alternate": alt.data if alt else None,
        "articles": [
            a
            for a in articles_view(db, context, origin=origin)
            if a["analysis"]
            and sid in [x["supplier_id"] for x in a["analysis"]["assessments"]]
        ],
    }


@app.get("/api/materials")
def materials(db: Session = Depends(get_db)):
    return [m.data for m in db.scalars(select(Material).order_by(Material.id))]


@app.get("/api/materials/{mid}")
def material(mid: str, db: Session = Depends(get_db)):
    m = db.get(Material, mid)
    if not m:
        raise HTTPException(404, "Material no encontrado")
    primary = db.get(Supplier, m.data["primary_id"])
    alternate = (
        db.get(Supplier, m.data["alternate_id"]) if m.data["alternate_id"] else None
    )
    return {
        **m.data,
        "primary": primary.data if primary else None,
        "alternate": alternate.data if alternate else None,
    }


@app.get("/api/articles")
def articles(
    origin: str = "",
    context: Literal["exercise", "rss"] = "exercise",
    q: str = "",
    state: str = "",
    source: str = "",
    event_type: str = "",
    date_from: str = "",
    date_to: str = "",
    relevant: bool = False,
    db: Session = Depends(get_db),
):
    rows = articles_view(db, context, origin=origin)
    return [
        a
        for a in rows
        if (not q or q.casefold() in (a["headline"] + " " + a["summary"]).casefold())
        and (not state or a["state"] == state)
        and (not source or a["source"] == source)
        and (
            not event_type
            or a["analysis"]
            and event_type
            in (
                a["analysis"]["event_type"],
                (a["analysis"].get("event_classification") or {}).get("category"),
            )
        )
        and (not date_from or a["published_date"] >= date_from)
        and (not date_to or a["published_date"][:10] <= date_to)
        and (not relevant or a["analysis"] and a["analysis"]["affected_supplier_ids"])
    ]


@app.get("/api/articles/{aid}")
def article(aid: str, db: Session = Depends(get_db)):
    a = db.get(Article, aid)
    if not a:
        raise HTTPException(404, "Noticia no encontrada")
    from app.queue import analysis_key
    current_job = db.scalar(select(Job).where(Job.key == analysis_key(a)))
    return {**article_view(db, a), "analysis_job": {"id": current_job.id, "state": current_job.state, "error": current_job.error, "analysis_profile": current_job.payload.get("analysis_profile", LEGACY_PROFILE)} if current_job else None}


@app.get("/api/sources")
def sources(db: Session = Depends(get_db)):
    return sources_view(db)


@app.post("/api/imports", dependencies=[Depends(presenter)])
async def imports(file: UploadFile = File(...), db: Session = Depends(get_db)):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        batch, diagnostic = import_excel(db, data, file.filename or "")
        db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc, ValueError):
            raise HTTPException(422, str(exc))
        raise HTTPException(
            422, "No se pudo importar el archivo. Revisa esquema y formato XLSX."
        )
    return {"batch_id": batch.id, **diagnostic}


@app.get("/api/batches")
def batches(db: Session = Depends(get_db)):
    out = []
    for b in db.scalars(select(Batch).order_by(Batch.created_at)):
        rows = db.scalars(select(Article).where(Article.batch_id == b.id)).all()
        from app.queue import analysis_key

        keys = [analysis_key(a) for a in rows]
        jobs = db.scalars(select(Job).where(Job.key.in_(keys))).all()
        from collections import Counter
        generations = {a.id: a.generation for a in rows}
        latest_results = {}
        for analysis in db.scalars(select(Analysis).where(Analysis.article_id.in_(generations)).order_by(Analysis.created_at.desc())):
            if analysis.generation == generations[analysis.article_id]:
                latest_results.setdefault(analysis.article_id, analysis.result)
        profiles = Counter((r.get("analysis_profile", r.get("question_version", "no registrado")), r.get("question_version"), r.get("analysis_versions", {}).get("review", r.get("review_policy_version", "no registrada"))) for r in latest_results.values())
        out.append(
            {
                "id": b.id,
                "split": b.split,
                "filename": b.filename,
                "analysis_profiles": [{"profile": p, "questions": q, "review": v, "count": n} for (p,q,v),n in sorted(profiles.items(),key=lambda x:str(x[0]))],
                "mixed_profiles": len(profiles) > 1,
                "origin_label": batch_label(b),
                "count": b.count,
                "logical_date": b.logical_date,
                "done": sum(a.state in ("done", "review") for a in rows),
                "errors": sum(a.state == "error" for a in rows),
                "pending": sum(a.state == "pending" for a in rows),
                "queued": sum(j.state == "queued" for j in jobs),
                "running": sum(j.state == "running" for j in jobs),
                "job_errors": sum(j.state == "error" for j in jobs),
                "started_at": b.started_at,
                "completed_at": b.completed_at,
                "elapsed_seconds": (b.completed_at - b.started_at).total_seconds()
                if b.completed_at and b.started_at
                else None,
            }
        )
    return out


class AnalysisSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_profile: Literal["1.0.0", "link-2.2.0", "radar-1.0.0-candidate"] = DEFAULT_PROFILE


@app.post("/api/batches/{bid}/analyze", status_code=202, dependencies=[Depends(presenter)])
def analyze(bid: str, body: AnalysisSelection | None = None, db: Session = Depends(get_db)):
    from app.queue import enqueue_batch

    require_current_worker(db)
    try:
        jobs = enqueue_batch(db, bid, (body or AnalysisSelection()).analysis_profile)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    return {"job_ids": jobs}


@app.get("/api/jobs/{jid}")
def job(jid: str, db: Session = Depends(get_db)):
    j = db.get(Job, jid)
    if not j:
        raise HTTPException(404, "Trabajo no encontrado")
    calls = []
    if j.kind == "analysis" and j.payload.get("article_id"):
        generation = j.payload.get("generation", 0)
        run_key = f"{j.payload['article_id']}:generation:{generation}" if generation else ""
        calls = db.scalars(select(ApiCall).where(ApiCall.article_id == j.payload["article_id"], ApiCall.run_key == run_key).order_by(ApiCall.created_at)).all()
    steps = {"a": "Identificación y candidatos", "b": "Exposición, riesgo y urgencia", "candidate_support": "Soporte de las decisiones", "candidate_followup": "Dudas de alcance y urgencia"}
    last = next((c for c in reversed(calls) if c.status == 200), None)
    return {
        "id": j.id,
        "kind": j.kind,
        "analysis_profile": j.payload.get("analysis_profile", LEGACY_PROFILE),
        "profile_snapshot": j.payload.get("profile_snapshot"),
        "telemetry": j.payload.get("telemetry"),
        "last_completed_step": (steps.get(last.stage.split(".part")[0], last.stage.split(".part")[0]) + (" · grupo " + last.stage.split(".part")[1] if ".part" in last.stage else "")) if last else None,
        "state": j.state,
        "attempts": j.attempts,
        "heartbeat": j.heartbeat,
        "error": j.error,
        "source_id": j.payload.get("source_id"),
        "article_id": j.payload.get("article_id"),
        "network_requests": len(calls) if j.kind == "analysis" else None,
    }


class DiagnosticRetry(BaseModel):
    reason: str = Field(min_length=12, max_length=2000)


@app.get("/api/articles/{aid}/execution", dependencies=[Depends(presenter)])
def article_execution(aid: str, include_payloads: bool = False, db: Session = Depends(get_db)):
    from app.execution_audit import view
    article = db.get(Article, aid)
    if not article:
        raise HTTPException(404, "Noticia no encontrada")
    return view(db, article, include_payloads)


@app.post("/api/articles/{aid}/diagnose", dependencies=[Depends(presenter)])
def diagnose_article(aid: str, body: DiagnosticRetry, db: Session = Depends(get_db)):
    article = db.get(Article, aid)
    if not article:
        raise HTTPException(404, "Noticia no encontrada")
    generation_key = f"{aid}:generation:{article.generation}" if article.generation else ""
    ids = []
    for call in db.scalars(select(ApiCall).where(ApiCall.article_id == aid, ApiCall.run_key == generation_key).with_for_update()):
        error = call.usage.get("_error", "")
        if not call.usage.get("_diagnosed_at") and (call.status in (400,401,403,422) or error.startswith("CONTRACT") or error == "MODEL_MISMATCH"):
            call.usage = {**call.usage, "_diagnosed_at": now().isoformat(), "_diagnosis_reason": body.reason}
            ids.append(call.id)
    db.commit()
    return {"diagnosed_calls": ids, "generation": article.generation, "counters_preserved": True}


@app.post(
    "/api/articles/{aid}/retry", status_code=202, dependencies=[Depends(presenter)]
)
def retry_article(aid: str, body: DiagnosticRetry, db: Session = Depends(get_db)):
    require_current_worker(db)
    a = db.get(Article, aid)
    key = "analysis:" + aid + (f":g{a.generation}" if a and a.generation else "")
    job = db.scalar(select(Job).where(Job.key == key).with_for_update())
    if not a or not job or a.state != "error" or job.state != "error":
        raise HTTPException(
            409, "Solo se reintenta un error diagnosticado con trabajo existente"
        )
    from app.profiles import CANDIDATE_PROFILE, candidate_versions
    if job.payload.get("analysis_profile") == CANDIDATE_PROFILE and job.payload.get("analysis_versions") != candidate_versions():
        # This is a new versioned execution, not a reset of the failed job.
        diagnose_article(aid, body, db)
        from app.reanalysis import enqueue_article
        try:
            replacement = enqueue_article(db, aid, CANDIDATE_PROFILE)
            db.commit()
        except ValueError as exc:
            db.rollback()
            raise HTTPException(409, str(exc))
        return {"job_id": replacement.id, "state": "queued", "generation": a.generation, "profile_updated": True, "history_preserved": True}
    if job.attempts >= 3:
        raise HTTPException(
            409, "Agotados los intentos del trabajo; no se reinicia el presupuesto"
        )
    stages = db.execute(
        select(ApiCall.stage, func.count())
        .where(
            ApiCall.article_id == aid,
            ApiCall.run_key
            == (f"{a.id}:generation:{a.generation}" if a.generation else ""),
        )
        .group_by(ApiCall.stage)
    ).all()
    if any(count >= 3 for stage, count in stages):
        raise HTTPException(
            409, "Agotados los tres intentos por etapa; no se generan nuevas llamadas"
        )
    job.payload = {
        **job.payload,
        "diagnostic_ack_at": now().isoformat(),
        "diagnostic_reason": body.reason,
    }
    job.state = "queued"
    job.error = None
    job.next_attempt_at = now()
    a.state = "pending"
    db.commit()
    return {"job_id": job.id, "state": "queued"}


@app.get("/api/batches/{bid}/export.xlsx", dependencies=[Depends(presenter)])
def export(bid: str, db: Session = Depends(get_db)):
    try:
        data = export_batch(db, bid)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="supplier-risk-resultados.xlsx"'
        },
    )


@app.post("/api/sources/sync", status_code=202, dependencies=[Depends(presenter)])
def sync(db: Session = Depends(get_db)):
    from app.queue import enqueue_sync
    from app.cli import seed

    seed(db)
    jobs = enqueue_sync(db, manual=True)
    db.commit()
    return {"job_ids": jobs, "worker": worker_status(db)}


@app.get("/api/worker")
def worker_status(db: Session = Depends(get_db)):
    from datetime import timedelta

    recent = db.scalars(
        select(WorkerPresence)
        .where(WorkerPresence.heartbeat > now() - timedelta(seconds=30))
        .order_by(WorkerPresence.heartbeat.desc())
    ).all()
    latest = db.scalar(select(func.max(WorkerPresence.heartbeat)))
    revision = os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "local"
    return {
        "online": bool(recent),
        "compatible": bool(recent) and all(w.revision == revision for w in recent),
        "revision": recent[0].revision if recent else None,
        "expected_revision": revision,
        "last_seen_at": latest,
    }


def require_current_worker(db):
    status = worker_status(db)
    if not status["online"]:
        raise HTTPException(
            409, "El worker debe estar conectado antes de iniciar un lote JEV."
        )
    if not status["compatible"]:
        raise HTTPException(
            409,
            "Hay workers con otra versión. Actualiza el worker y espera 30 segundos antes de analizar.",
        )


@app.get("/api/analysis/budget", dependencies=[Depends(presenter)])
def analysis_budget(db: Session = Depends(get_db)):
    from app.queue import budget_available

    grants = db.scalars(select(Grant).where(Grant.split == "rss")).all()
    active = [
        g
        for g in grants
        if (not g.expires_at or g.expires_at > now())
        and (not g.budget_id or budget_available(db, g.budget_id))
    ]
    unlimited = any(g.article_limit is None for g in active)
    daily_used = db.scalar(
        select(func.count())
        .select_from(RssDailyUsage)
        .where(
            RssDailyUsage.reserved_at
            >= now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
    )
    daily_remaining = max(0, RSS["daily_analysis_budget"] - daily_used)
    enforce = settings.jev_budget_limits_enabled
    return {
        "limits_enforced": enforce,
        "pending_articles": db.scalar(
            select(func.count())
            .select_from(Article)
            .where(Article.context == "rss", Article.state == "pending")
        ),
        "unlimited": not enforce or unlimited,
        "daily_limit": RSS["daily_analysis_budget"] if enforce else None,
        "daily_remaining": daily_remaining if enforce else None,
        "remaining": None
        if not enforce
        else min(
            daily_remaining,
            daily_remaining
            if unlimited
            else sum(max(0, g.article_limit - g.used) for g in active),
        ),
        "reserved": sum(g.used for g in grants),
        "periodic_enabled": settings.rss_analysis_enabled,
        "request_budgets": budget_status(db)["budgets"],
        "maximum_requests_per_article": 6,
        "network_requests": db.scalar(
            select(func.count())
            .select_from(ApiCall)
            .join(Article, Article.id == ApiCall.article_id)
            .where(Article.context == "rss")
        ),
    }


@app.get("/api/admin/budgets", dependencies=[Depends(presenter)])
def budget_status(db: Session = Depends(get_db)):
    from datetime import timedelta

    return {
        "limits_enforced": settings.jev_budget_limits_enabled,
        "budgets": [
            {
                "id": b.id,
                "enforced": settings.jev_budget_limits_enabled
                and b.request_limit is not None,
                "request_limit": b.request_limit,
                "requests_used": b.requests_used,
                "remaining_requests": None
                if b.request_limit is None
                else (
                    max(0, b.request_limit - b.requests_used)
                    if not b.window_seconds
                    or not b.started_at
                    or now() < b.started_at + timedelta(seconds=b.window_seconds)
                    else 0
                ),
                "unlimited": b.request_limit is None,
                "started_at": b.started_at,
                "closes_at": b.started_at + timedelta(seconds=b.window_seconds)
                if b.started_at and b.window_seconds
                else None,
            }
            for b in db.scalars(
                select(ConsumptionBudget).order_by(ConsumptionBudget.id)
            )
        ],
        "grants": [
            {
                "id": g.id,
                "split": g.split,
                "article_limit": g.article_limit,
                "used": g.used,
                "budget_id": g.budget_id,
                "expires_at": g.expires_at,
            }
            for g in db.scalars(select(Grant).order_by(Grant.id))
        ],
    }


@app.post("/api/admin/budgets/{budget_id}/diagnose", dependencies=[Depends(presenter)])
def acknowledge_diagnosis(
    budget_id: str, body: DiagnosticRetry, db: Session = Depends(get_db)
):
    budget = db.scalar(
        select(ConsumptionBudget)
        .where(ConsumptionBudget.id == budget_id)
        .with_for_update()
    )
    if not budget:
        raise HTTPException(404, "Presupuesto no encontrado")
    diagnosed = []
    for call in db.scalars(
        select(ApiCall).where(ApiCall.budget_id == budget_id).with_for_update()
    ):
        error = call.usage.get("_error", "")
        if not call.usage.get("_diagnosed_at") and (
            call.status in (400, 401, 403, 422)
            or error.startswith("CONTRACT")
            or error == "MODEL_MISMATCH"
        ):
            call.usage = {
                **call.usage,
                "_diagnosed_at": now().isoformat(),
                "_diagnosis_reason": body.reason,
            }
            diagnosed.append(call.id)
    db.commit()
    return {"diagnosed_calls": diagnosed, "requests_used": budget.requests_used}


@app.get("/api/batches/{bid}/execution", dependencies=[Depends(presenter)])
def batch_execution(bid: str, db: Session = Depends(get_db)):
    if not db.get(Batch, bid):
        raise HTTPException(404, "Lote no encontrado")
    rows = db.execute(
        select(ApiCall, Article.news_id)
        .join(Article, Article.id == ApiCall.article_id)
        .where(Article.batch_id == bid)
        .order_by(ApiCall.created_at)
    ).all()
    return {
        "calls": [
            {
                "id": c.id,
                "news_id": news_id,
                "stage": c.stage,
                "attempt": c.attempt,
                "model": c.model,
                "http_status": c.status,
                "seconds": c.duration,
                "budget_id": c.budget_id,
                "error": c.usage.get("_error"),
                "contract_diagnostic": c.usage.get("_contract"),
                "score_diagnostics": c.usage.get("_score_diagnostics", []),
                "usage": {
                    k: v
                    for k, v in c.usage.items()
                    if k in ("input_tokens", "output_tokens", "total_tokens")
                    and isinstance(v, (int, float))
                },
            }
            for c, news_id in rows
        ]
    }


class ManualRssAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int | None = Field(default=None, ge=1)
    article_ids: list[str] | None = Field(default=None, min_length=1, max_length=10)
    analysis_profile: Literal["1.0.0", "radar-1.0.0-candidate"] = DEFAULT_PROFILE


@app.post("/api/analysis/rss", status_code=202, dependencies=[Depends(presenter)])
def analyze_rss(body: ManualRssAnalysis, db: Session = Depends(get_db)):
    from app.queue import enqueue_rss_analysis

    require_current_worker(db)
    if db.scalar(select(func.count()).select_from(Supplier)) != 40:
        raise HTTPException(409, "Importa primero las 40 identidades de la cartera.")
    if body.article_ids:
        if len(set(body.article_ids)) != len(body.article_ids): raise HTTPException(422, "Selección con IDs repetidos")
        chosen = db.scalars(select(Article).where(Article.id.in_(body.article_ids))).all()
        if len(chosen) != len(body.article_ids) or any(a.context != "rss" or a.state != "pending" for a in chosen):
            raise HTTPException(409, "La selección cambió: selecciona solo noticias RSS pendientes y recarga antes de analizar.")
    jobs = enqueue_rss_analysis(db, body.limit, article_ids=body.article_ids, profile=body.analysis_profile)
    if not jobs:
        db.rollback()
        raise HTTPException(
            409, "No hay noticias pendientes sin un trabajo de análisis en la cola."
        )
    db.commit()
    from app.profiles import maximum_requests
    return {"job_ids": jobs, "articles": len(jobs), "maximum_requests": len(jobs) * maximum_requests(body.analysis_profile)}


@app.post("/api/articles/{aid}/analyze", status_code=202, dependencies=[Depends(presenter)])
def analyze_article(aid: str, body: AnalysisSelection = AnalysisSelection(), db: Session = Depends(get_db)):
    from app.reanalysis import enqueue_article
    from app.profiles import maximum_requests
    require_current_worker(db)
    try:
        j = enqueue_article(db, aid, body.analysis_profile)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    return {"job_ids": [j.id], "maximum_requests": maximum_requests(body.analysis_profile), "analysis_profile": body.analysis_profile}


class PendingSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    article_ids: list[str] = Field(min_length=1)
    context: Literal["exercise", "rss"]
    analysis_profile: Literal["1.0.0", "radar-1.0.0-candidate"] = DEFAULT_PROFILE


@app.post("/api/analysis/pending", status_code=202, dependencies=[Depends(presenter)])
def analyze_pending(body: PendingSelection, db: Session = Depends(get_db)):
    from app.pending_selection import create
    require_current_worker(db)
    try:
        result = create(db, body.request_id, body.article_ids, body.context, body.analysis_profile)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@app.get("/api/analysis/pending/{selection_id}", dependencies=[Depends(presenter)])
def pending_progress(selection_id: str, db: Session = Depends(get_db)):
    from app.pending_selection import KIND, view
    manifest = db.get(Job, selection_id)
    if not manifest or manifest.kind != KIND:
        raise HTTPException(404, "Selección no encontrada")
    return view(db, manifest)


class DemoSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection: list[str] = Field(max_length=500)
    mode: Literal["delete", "rerun"] = "delete"
    analysis_profile: Literal["1.0.0", "link-2.2.0", "radar-1.0.0-candidate"] = DEFAULT_PROFILE


@app.get("/api/demo/options", dependencies=[Depends(presenter)])
def demo_options(db: Session = Depends(get_db)):
    from app.demo import options

    return options(db)


@app.post("/api/demo/preview", dependencies=[Depends(presenter)])
def selected_demo_preview(body: DemoSelection, db: Session = Depends(get_db)):
    from app.demo import preview

    try:
        return preview(db, body.selection, body.mode, body.analysis_profile)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post(
    "/api/articles/{aid}/compare", status_code=202, dependencies=[Depends(presenter)]
)
def compare_article(aid: str, db: Session = Depends(get_db)):
    from app.comparison import enqueue_comparison

    require_current_worker(db)
    try:
        comparison, job = enqueue_comparison(db, aid)
        db.commit()
        return {
            "comparison_id": comparison.id,
            "job_id": job.id,
            "maximum_requests": 3 * __import__("app.profiles", fromlist=["maximum_requests"]).maximum_requests(job.payload.get("analysis_profile", LEGACY_PROFILE)),
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@app.get("/api/articles/{aid}/comparisons", dependencies=[Depends(presenter)])
def comparisons(aid: str, db: Session = Depends(get_db)):
    from app.comparison import view

    return [
        view(db, row)
        for row in db.scalars(
            select(Comparison)
            .where(Comparison.article_id == aid)
            .order_by(Comparison.created_at.desc())
        )
    ]


@app.get("/api/articles/{aid}/runs", dependencies=[Depends(presenter)])
def analysis_runs(aid: str, db: Session = Depends(get_db)):
    return [
        {
            "id": r.id,
            "generation": r.generation,
            "created_at": r.created_at,
            "result": r.result,
            "cached": r.cached,
        }
        for r in db.scalars(
            select(Analysis)
            .where(Analysis.article_id == aid)
            .order_by(Analysis.generation.desc())
        )
    ]


@app.get("/api/demo/cleanup-preview", dependencies=[Depends(presenter)])
def demo_preview(db: Session = Depends(get_db)):
    from app.demo import preview

    return preview(db)


class DemoCleanup(BaseModel):
    confirmation: Literal["LIMPIAR DEMO", "REANALIZAR"]
    token: str = Field(max_length=20000)


@app.post("/api/demo/cleanup", dependencies=[Depends(presenter)])
def demo_cleanup(body: DemoCleanup, db: Session = Depends(get_db)):
    from app.demo import cleanup

    try:
        try:
            approved = codec().loads(body.token)
        except Exception:
            raise ValueError("Confirmación inválida. Revisa la vista previa.")
        expected = "REANALIZAR" if approved.get("mode") == "rerun" else "LIMPIAR DEMO"
        if body.confirmation != expected:
            raise ValueError("La confirmación no corresponde a la acción elegida.")
        if approved.get("mode") == "rerun":
            require_current_worker(db)
        counts = cleanup(db, body.token)
        db.commit()
        return {"deleted": counts}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@app.post("/api/qa/audio", status_code=202, dependencies=[Depends(presenter)])
def qa_audio():
    from app.qa_audio import sample
    return sample()


@app.get("/api/alerts")
def alerts(
    after: int = 0,
    context: Literal["exercise", "rss"] = "exercise",
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Alert)
        .join(Incident)
        .where(Incident.context == context)
        .order_by(Alert.id)
    ).all()
    from app.alert_scope import current as alert_current, reason as alert_reason
    incidents={i.id:i for i in db.scalars(select(Incident).where(Incident.context==context))}
    # Legacy alerts did not retain the category. Read the linked article,
    # never guess from its headline or the incident's canonical category.
    article_tags = {
        article.id: event_tag(result)
        for article, result in db.execute(
            select(Article, Analysis.result)
            .join(Analysis, Analysis.article_id == Article.id)
            .where(Article.context == context, Analysis.generation == Article.generation)
        ).all()
    }
    return {
        "items": [
            {
                "id": a.id,
                "incident_id": a.incident_id,
                "revision": a.revision,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at,
                **a.data,
                "is_current": alert_current(a,incidents.get(a.incident_id)),
                "historical_reason": alert_reason(a,incidents.get(a.incident_id)),
                "sound_eligible": bool(a.data.get("sound_eligible")) and alert_current(a,incidents.get(a.incident_id)),
                "event_tag": a.data.get("event_tag")
                or article_tags.get(a.data.get("article_id")),
            }
            for a in rows
            if a.id > after
        ],
        "cursor": max((a.id for a in rows), default=after),
        "unread": sum(not a.acknowledged and alert_current(a,incidents.get(a.incident_id)) for a in rows),
    }


@app.post("/api/alerts/{aid}/ack", dependencies=[Depends(presenter)])
def acknowledge(aid: int, db: Session = Depends(get_db)):
    a = db.get(Alert, aid)
    if not a:
        raise HTTPException(404, "Alerta no encontrada")
    a.acknowledged = True
    db.commit()
    return {"ok": True}


class Resolve(BaseModel):
    reason: str = Field(min_length=8, max_length=2000)


@app.post("/api/incidents/{iid}/resolve", dependencies=[Depends(presenter)])
def resolve(iid: str, body: Resolve, db: Session = Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incidente no encontrado")
    inc.history = [
        *inc.history,
        {"manual": True, "reason": body.reason, "at": now().isoformat()},
    ]
    inc.state = "resolved"
    inc.priority = 0
    inc.revision += 1
    for alert in db.scalars(select(Alert).where(Alert.incident_id == inc.id)):
        alert.data = {**alert.data, "state": "resolved", "sound_eligible": False}
    db.commit()
    return {"ok": True}


class DraftInput(BaseModel):
    supplier_id: str
    incident_id: str
    kind: Literal["supplier", "alternate"] = "supplier"


class DraftEdit(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.post("/api/drafts", dependencies=[Depends(presenter)])
def draft(body: DraftInput, db: Session = Depends(get_db)):
    s = db.get(Supplier, body.supplier_id)
    inc = db.get(Incident, body.incident_id)
    if not s or not inc or inc.supplier_id != s.id:
        raise HTTPException(422, "Se requiere un incidente validado del proveedor")
    from app.drafts import make_draft

    try:
        content = make_draft(db, s, inc, body.kind)
    except ValueError as e:
        raise HTTPException(409, str(e))
    d = Draft(
        supplier_id=s.id,
        incident_id=inc.id,
        article_id=__import__("app.views",fromlist=["current"]).current(inc).get("article_id"),
        evidence_snapshot={"incident_id":inc.id,"revision":inc.revision,"entry":__import__("app.views",fromlist=["current"]).current(inc)},
        kind=body.kind,
        text=content,
        context_hash=digest(inc.history),
    )
    db.add(d)
    db.commit()
    return {"id": d.id, "text": d.text}


@app.get("/api/model/candidates", dependencies=[Depends(presenter)])
def model_candidates():
    return json.loads((ROOT / "app/model_candidates.json").read_text())


@app.get("/api/model/operational-candidate", dependencies=[Depends(presenter)])
def operational_candidate_evaluation():
    return json.loads((ROOT / "app/window_evaluation.json").read_text())


@app.get("/api/model/review-policy", dependencies=[Depends(presenter)])
def review_policy_evaluation():
    # Aggregate development evidence only. Never exposes case references or
    # reclassifies historical articles when the dashboard is opened.
    return json.loads((ROOT / "app/review_evaluation.json").read_text())


class VerificationInput(BaseModel):
    article_id: str
    supplier_id: str = Field(pattern=r"^S\d{3}$")
    generation: int = Field(ge=0)
    version: int = Field(ge=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=3)
    note: str = Field(min_length=12, max_length=500)
    acknowledged: Literal[True]


@app.post("/api/verification-drafts", status_code=201, dependencies=[Depends(presenter)])
def verification_draft(body: VerificationInput, db: Session = Depends(get_db)):
    from app.verification import prepare
    article = db.scalar(select(Article).where(Article.id == body.article_id).with_for_update())
    supplier = db.get(Supplier, body.supplier_id)
    if not article or not supplier:
        raise HTTPException(404, "Noticia o proveedor no encontrado")
    if article.generation != body.generation or article.version != body.version:
        raise HTTPException(409, "La noticia cambió; revisa los fragmentos antes de crear otra consulta.")
    analysis = db.scalar(select(Analysis).where(Analysis.article_id == article.id, Analysis.generation == article.generation).order_by(Analysis.created_at.desc()))
    if not analysis or article.state not in ("done", "review"):
        raise HTTPException(409, "Espera a que termine el análisis de esta noticia.")
    try:
        content, snapshot, context_hash = prepare(article, supplier, analysis.result, body.evidence_ids, body.note)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    draft = Draft(supplier_id=supplier.id, incident_id=None, article_id=article.id, kind="verification", text=content, evidence_snapshot=snapshot, context_hash=context_hash)
    db.add(draft)
    db.commit()
    return {"id": draft.id, "text": draft.text, "kind": "verification", "exposure_status": "potential_unconfirmed"}


@app.get("/api/articles/{aid}/drafts", dependencies=[Depends(presenter)])
def article_drafts(aid: str, db: Session = Depends(get_db)):
    return [{"id": d.id, "supplier_id": d.supplier_id, "kind": d.kind} for d in db.scalars(select(Draft).where(Draft.article_id == aid).order_by(Draft.id))]


@app.get("/api/suppliers/{sid}/verification-drafts", dependencies=[Depends(presenter)])
def supplier_verification_drafts(sid: str, db: Session = Depends(get_db)):
    return [{"id": d.id, "article_id": d.article_id, "snapshot": d.evidence_snapshot} for d in db.scalars(select(Draft).where(Draft.supplier_id == sid, Draft.kind == "verification").order_by(Draft.id))]


@app.get("/api/drafts/{did}", dependencies=[Depends(presenter)])
def read_draft(did: str, db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404, "Borrador no encontrado")
    return {"id": d.id, "text": d.text, "kind": d.kind, "supplier_id": d.supplier_id, "evidence_snapshot": d.evidence_snapshot}


@app.patch("/api/drafts/{did}", dependencies=[Depends(presenter)])
def edit_draft(did: str, body: DraftEdit, db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404, "Borrador no encontrado")
    d.text = body.text
    db.commit()
    return {"id": d.id, "text": d.text}


@app.get("/api/model/metrics", dependencies=[Depends(presenter)])
def model_metrics(
    context: Literal["exercise", "rss"] = "exercise",
    origin: str = "",
    db: Session = Depends(get_db),
):
    from app.model_metrics import model_metrics as calculate

    return calculate(db, context, origin)


@app.get("/api/model/diagnostics/{bid}", dependencies=[Depends(presenter)])
def model_diagnostics(bid: str, db: Session = Depends(get_db)):
    from app.diagnostics import diagnose_batch
    try:
        return diagnose_batch(db, bid)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/evaluations/{bid}", dependencies=[Depends(presenter)])
def evaluate(bid: str, db: Session = Depends(get_db)):
    from app.evaluation import evaluate_batch

    try:
        return evaluate_batch(db, bid)
    except ValueError as e:
        raise HTTPException(409, str(e))


# Human operations are deliberately separate from Analysis/EvaluationLabel.
from app.human_review import DecisionInput, ReviewConflict
from app.incident_work import WorkInput

@app.get("/api/articles/{aid}/review", dependencies=[Depends(presenter)])
def read_human_review(aid: str, db: Session = Depends(get_db)):
    from app.human_review import view
    article = db.get(Article, aid)
    if not article: raise HTTPException(404, "Noticia no encontrada")
    return view(db, article)

@app.post("/api/articles/{aid}/review", status_code=201, dependencies=[Depends(presenter)])
def write_human_review(aid: str, body: DecisionInput, db: Session = Depends(get_db)):
    from app.human_review import save, view
    try:
        save(db, aid, body); db.commit()
        return view(db, db.get(Article, aid))
    except ValueError as exc:
        db.rollback(); raise HTTPException(409 if isinstance(exc, ReviewConflict) else 422, str(exc))

@app.get("/api/incidents/{iid}/workspace", dependencies=[Depends(presenter)])
def read_incident_work(iid: str, db: Session = Depends(get_db)):
    from app.incident_work import view
    inc = db.get(Incident, iid)
    if not inc: raise HTTPException(404, "Incidente no encontrado")
    return view(db, inc)

@app.post("/api/incidents/{iid}/workspace", status_code=201, dependencies=[Depends(presenter)])
def write_incident_work(iid: str, body: WorkInput, db: Session = Depends(get_db)):
    from app.incident_work import save, view
    try:
        save(db, iid, body); db.commit()
        return view(db, db.get(Incident, iid))
    except ValueError as exc:
        db.rollback(); raise HTTPException(409 if isinstance(exc, ReviewConflict) else 422, str(exc))

# Private comparative campaigns. Public routes never expose evaluation references.
class CampaignInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=5, max_length=120)
    inputs: list[dict] = Field(min_length=1, max_length=200)
    suppliers: list[dict] = Field(min_length=40, max_length=40)
    materials: list[dict] = Field(default_factory=list, max_length=100)
    manifest: dict

@app.get('/api/campaigns', dependencies=[Depends(presenter)])
def campaign_list(db: Session = Depends(get_db)):
    from app.campaigns import listing
    return listing(db)

@app.post('/api/campaigns', status_code=201, dependencies=[Depends(presenter)])
def campaign_prepare(body: CampaignInput, db: Session = Depends(get_db)):
    from app.campaigns import prepare
    try:
        c=prepare(db,body.model_dump());return {'id':c.id,'state':c.state,'freeze':{k:v for k,v in c.freeze.items() if k not in ('inputs','suppliers','materials')}}
    except (ValueError,KeyError,TypeError):
        db.rollback();raise HTTPException(422,'Entradas o catálogo no válidos para congelar la campaña.')

@app.post('/api/campaigns/import', status_code=201, dependencies=[Depends(presenter)])
async def campaign_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    from app.campaigns import import_completed
    raw=await file.read(30_000_001)
    if len(raw)>30_000_000:raise HTTPException(413,'Campaña superior a30MB')
    try:
        c=import_completed(db,json.loads(raw));return {'id':c.id,'state':c.state,'new_inference':False}
    except (ValueError,KeyError,TypeError):
        db.rollback();raise HTTPException(422,'Campaña no válida o distinta de resultados ya guardados.')

@app.post('/api/campaigns/{cid}/start', status_code=202, dependencies=[Depends(presenter)])
def campaign_start(cid: str, db: Session = Depends(get_db)):
    from app.campaigns import start
    try:
        c=start(db,cid);return {'id':c.id,'state':c.state}
    except ValueError as exc:
        db.rollback();raise HTTPException(409,str(exc))

@app.get('/api/campaigns/{cid}', dependencies=[Depends(presenter)])
def campaign_report(cid: str, split: Literal['training','validation','test','liveday','labelled','all']='training', db: Session = Depends(get_db)):
    from app.campaigns import report
    try:return report(db,cid,split)
    except ValueError:raise HTTPException(404,'Campaña no encontrada')

@app.get('/api/campaigns/{cid}/export', dependencies=[Depends(presenter)])
def campaign_export(cid: str, db: Session = Depends(get_db)):
    from app.campaigns import report
    try: result=report(db,cid,'all',full=True)
    except ValueError:raise HTTPException(404,'Campaña no encontrada')
    return Response(json.dumps(result,default=str,ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="campana-{cid}.json"'})



class CampaignDiagnosis(BaseModel):
    note: str = Field(min_length=15, max_length=1000)

@app.post('/api/campaigns/{cid}/diagnose', dependencies=[Depends(presenter)])
def campaign_diagnose(cid: str, body: CampaignDiagnosis, db: Session = Depends(get_db)):
    c=db.get(EvaluationCampaign,cid)
    if not c or c.state!='paused':raise HTTPException(409,'La campaña no está pausada')
    stamp=now().isoformat()
    # Mark the acknowledged machine errors; retain every failed result and attempt.
    for call in db.scalars(select(ApiCall).where(ApiCall.budget_id=='campaign:'+cid)):
        if call.status in (400,401,403,422) or str(call.usage.get('_error','')).startswith('CONTRACT'):
            call.usage={**call.usage,'_diagnosed_at':stamp,'_diagnosis':body.note}
    c.freeze={**c.freeze,'diagnosis_history':[ *c.freeze.get('diagnosis_history',[]),{'at':stamp,'note':body.note}]}
    c.state='prepared';db.commit()
    return {'state':c.state,'message':'Fallos conservados; reanudar solo ejecuta entradas pendientes, nunca repite predicciones válidas.'}


@app.get("/api/model/final")
def final_profile_report(sample: Literal["training", "validation", "labelled"] = "labelled", db: Session = Depends(get_db)):
    from app.final_model import report
    return report(db, sample)

static = ROOT / "frontend/dist"
if (static / "assets").exists():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    if path.startswith(("api/", "inputs/", "evidence/", ".", "config/", "contracts/")):
        raise HTTPException(404, "Recurso no público")
    if not (static / "index.html").exists():
        raise HTTPException(503, "Frontend pendiente de compilar")
    return FileResponse(static / "index.html")
