import io, json
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db import get_db
from app.settings import settings, ROOT, POLICY
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
    return {"status": "ok"}


@app.get("/readyz")
def ready(db: Session = Depends(get_db)):
    try:
        revision = db.execute(
            text("select version_num from alembic_version")
        ).scalar_one()
        if revision != "0002":
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
    }


class DiagnosticRetry(BaseModel):
    reason: str = Field(min_length=12, max_length=2000)


@app.post(
    "/api/articles/{aid}/retry", status_code=202, dependencies=[Depends(presenter)]
)
def retry_article(aid: str, body: DiagnosticRetry, db: Session = Depends(get_db)):
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

    jobs = enqueue_sync(db, manual=True)
    db.commit()
    return {"job_ids": jobs}


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
