import io, json, os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db import get_db, DatabaseConfigurationError
from app.settings import settings, ROOT, POLICY, RSS
from app.models import *
from app.auth import presenter, identity, login, codec
from app.importer import import_excel, export_batch, digest
from app.views import suppliers_view, articles_view, sources_view, article_view

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
        if revision != "0005":
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
    return {
        "model": settings.jev_model,
        "policy_version": POLICY["version"],
        "question_version": POLICY["question_version"],
        "engine_configured": bool(settings.typesafe_api_key.get_secret_value()),
        "bands": POLICY["bands"],
        "cooldown_seconds": POLICY["audio"]["cooldown_seconds"],
        "fixtures": settings.demo_fixtures_enabled,
        "rss_paid_analysis": settings.rss_analysis_enabled,
    }


@app.get("/api/admin/config", dependencies=[Depends(presenter)])
def admin_config():
    return settings.credential_status()


@app.get("/api/overview")
def overview(
    context: Literal["exercise", "rss"] = "exercise", db: Session = Depends(get_db)
):
    suppliers = suppliers_view(db, context)
    articles = articles_view(db, context)
    sources = sources_view(db)
    processed = [a for a in articles if a["state"] in ("done", "review")]
    return {
        "supplier_count": len(suppliers),
        "urgent_suppliers": sum(s["urgent"] for s in suppliers),
        "active_incidents": sum(s["incident_count"] for s in suppliers),
        "received": len(articles),
        "processed": len(processed),
        "pending": sum(a["state"] == "pending" for a in articles),
        "errors": sum(a["state"] == "error" for a in articles),
        "review": sum(a["state"] == "review" for a in articles),
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
        "latencies": latencies(db, context),
    }


def latencies(db, context):
    values = sorted(
        db.scalars(
            select(Analysis.duration).join(Article).where(Article.context == context)
        ).all()
    )
    return {
        "n": len(values),
        "p50": values[int((len(values) - 1) * 0.50)] if values else None,
        "p95": values[int((len(values) - 1) * 0.95)] if values else None,
    }


@app.get("/api/suppliers")
def suppliers(
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
    rows = suppliers_view(db, context)
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
    db: Session = Depends(get_db),
):
    row = next(
        (s for s in suppliers_view(db, context) if s["supplier_id"] == sid), None
    )
    if not row:
        raise HTTPException(404, "Proveedor no encontrado")
    alt = db.get(Supplier, row["alternate_id"]) if row["alternate_id"] else None
    return {
        **row,
        "alternate": alt.data if alt else None,
        "articles": [
            a
            for a in articles_view(db, context)
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
    rows = articles_view(db, context)
    return [
        a
        for a in rows
        if (not q or q.casefold() in (a["headline"] + " " + a["summary"]).casefold())
        and (not state or a["state"] == state)
        and (not source or a["source"] == source)
        and (
            not event_type
            or a["analysis"]
            and a["analysis"]["event_type"] == event_type
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
    return article_view(db, a)


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
        out.append(
            {
                "id": b.id,
                "split": b.split,
                "count": b.count,
                "logical_date": b.logical_date,
                "done": sum(a.state in ("done", "review") for a in rows),
                "errors": sum(a.state == "error" for a in rows),
                "pending": sum(a.state == "pending" for a in rows),
                "started_at": b.started_at,
                "completed_at": b.completed_at,
                "elapsed_seconds": (b.completed_at - b.started_at).total_seconds()
                if b.completed_at and b.started_at
                else None,
            }
        )
    return out


@app.post(
    "/api/batches/{bid}/analyze", status_code=202, dependencies=[Depends(presenter)]
)
def analyze(bid: str, db: Session = Depends(get_db)):
    from app.queue import enqueue_batch

    require_current_worker(db)
    try:
        jobs = enqueue_batch(db, bid)
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
    return {
        "id": j.id,
        "kind": j.kind,
        "state": j.state,
        "attempts": j.attempts,
        "heartbeat": j.heartbeat,
        "error": j.error,
        "source_id": j.payload.get("source_id"),
        "article_id": j.payload.get("article_id"),
        "network_requests": db.scalar(
            select(func.count())
            .select_from(ApiCall)
            .where(ApiCall.article_id == j.payload["article_id"])
        )
        if j.kind == "analysis" and j.payload.get("article_id")
        else None,
    }


class DiagnosticRetry(BaseModel):
    reason: str = Field(min_length=12, max_length=2000)


@app.post(
    "/api/articles/{aid}/retry", status_code=202, dependencies=[Depends(presenter)]
)
def retry_article(aid: str, body: DiagnosticRetry, db: Session = Depends(get_db)):
    require_current_worker(db)
    a = db.get(Article, aid)
    job = db.scalar(select(Job).where(Job.key == "analysis:" + aid).with_for_update())
    if not a or not job or a.state != "error" or job.state != "error":
        raise HTTPException(
            409, "Solo se reintenta un error diagnosticado con trabajo existente"
        )
    if job.attempts >= 3:
        raise HTTPException(
            409, "Agotados los intentos del trabajo; no se reinicia el presupuesto"
        )
    stages = db.execute(
        select(ApiCall.stage, func.count())
        .where(ApiCall.article_id == aid)
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
        .select_from(GrantArticle)
        .join(Article)
        .where(
            Article.context == "rss",
            GrantArticle.reserved_at
            >= now().replace(hour=0, minute=0, second=0, microsecond=0),
        )
    )
    daily_remaining = max(0, RSS["daily_analysis_budget"] - daily_used)
    return {
        "unlimited": unlimited,
        "daily_limit": RSS["daily_analysis_budget"],
        "daily_remaining": daily_remaining,
        "remaining": min(
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
        "budgets": [
            {
                "id": b.id,
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
    limit: int = Field(ge=1, le=10)


@app.post("/api/analysis/rss", status_code=202, dependencies=[Depends(presenter)])
def analyze_rss(body: ManualRssAnalysis, db: Session = Depends(get_db)):
    from app.queue import enqueue_rss_analysis

    require_current_worker(db)
    if db.scalar(select(func.count()).select_from(Supplier)) != 40:
        raise HTTPException(409, "Importa primero las 40 identidades de la cartera.")
    jobs = enqueue_rss_analysis(db, body.limit)
    if not jobs:
        db.rollback()
        raise HTTPException(
            409, "Sin noticias pendientes o presupuesto RSS autorizado disponible."
        )
    db.commit()
    return {"job_ids": jobs, "articles": len(jobs), "maximum_requests": len(jobs) * 6}


@app.get("/api/demo/cleanup-preview", dependencies=[Depends(presenter)])
def demo_preview(db: Session = Depends(get_db)):
    from app.demo import preview

    return preview(db)


class DemoCleanup(BaseModel):
    confirmation: Literal["LIMPIAR DEMO"]
    token: str = Field(max_length=20000)


@app.post("/api/demo/cleanup", dependencies=[Depends(presenter)])
def demo_cleanup(body: DemoCleanup, db: Session = Depends(get_db)):
    from app.demo import cleanup

    try:
        counts = cleanup(db, body.token)
        db.commit()
        return {"deleted": counts}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


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
    return {
        "items": [
            {
                "id": a.id,
                "incident_id": a.incident_id,
                "revision": a.revision,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at,
                **a.data,
            }
            for a in rows
            if a.id > after
        ],
        "cursor": max((a.id for a in rows), default=after),
        "unread": sum(not a.acknowledged for a in rows),
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
        kind=body.kind,
        text=content,
        context_hash=digest(inc.history),
    )
    db.add(d)
    db.commit()
    return {"id": d.id, "text": d.text}


@app.patch("/api/drafts/{did}", dependencies=[Depends(presenter)])
def edit_draft(did: str, body: DraftEdit, db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404, "Borrador no encontrado")
    d.text = body.text
    db.commit()
    return {"id": d.id, "text": d.text}


@app.post("/api/evaluations/{bid}", dependencies=[Depends(presenter)])
def evaluate(bid: str, db: Session = Depends(get_db)):
    from app.evaluation import evaluate_batch

    try:
        return evaluate_batch(db, bid)
    except ValueError as e:
        raise HTTPException(409, str(e))


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
