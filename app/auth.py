import hashlib, hmac, secrets
from datetime import timedelta
from fastapi import HTTPException, Request, Depends
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import SessionRecord, LoginAttempt, now
from app.settings import settings


def codec():
    secret = settings.session_secret.get_secret_value()
    if not secret:
        raise HTTPException(503, "Sesión sin configurar")
    return URLSafeSerializer(secret, salt="radar-presenter-v1")


def identity(request: Request, db: Session):
    token = request.cookies.get("radar_session")
    if not token or not settings.session_secret.get_secret_value():
        return None
    try:
        sid = codec().loads(token)
    except BadSignature:
        return None
    record = db.get(SessionRecord, sid)
    return record if record and record.expires_at > now() else None


def presenter(request: Request, db: Session = Depends(get_db)):
    record = identity(request, db)
    if not record:
        raise HTTPException(401, "Acceso de presentador requerido")
    if request.method not in ("GET", "HEAD"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.app_base_url.rstrip("/"):
            raise HTTPException(403, "Origen no permitido")
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), record.csrf
        ):
            raise HTTPException(403, "Token CSRF inválido")
    return record


def login(request, db, password):
    if (
        not settings.admin_password.get_secret_value()
        or not settings.session_secret.get_secret_value()
    ):
        raise HTTPException(503, "Acceso de presentador sin configurar")
    peer = request.client.host if request.client else "unknown"
    key = hashlib.sha256(peer.encode()).hexdigest()
    attempt = db.get(LoginAttempt, key)
    if not attempt:
        attempt = LoginAttempt(id=key, count=0, window=now())
        db.add(attempt)
    if now() - attempt.window > timedelta(minutes=15):
        attempt.count = 0
        attempt.window = now()
    if attempt.count >= 8:
        raise HTTPException(429, "Demasiados intentos; espera 15 minutos")
    attempt.count += 1
    db.commit()
    if not hmac.compare_digest(
        password.encode(), settings.admin_password.get_secret_value().encode()
    ):
        raise HTTPException(401, "Contraseña incorrecta")
    attempt.count = 0
    record = SessionRecord(
        id=secrets.token_urlsafe(32),
        csrf=secrets.token_urlsafe(32),
        expires_at=now() + timedelta(hours=8),
    )
    db.add(record)
    db.commit()
    return record
