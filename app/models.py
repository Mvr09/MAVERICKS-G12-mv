from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Float,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    file_hash: Mapped[str] = mapped_column(String, unique=True)
    split: Mapped[str] = mapped_column(String)
    context: Mapped[str] = mapped_column(String, default="exercise")
    logical_date: Mapped[str | None] = mapped_column(String, nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    export_headers: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("origin_key", "version"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    origin_key: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("batches.id"))
    source_id: Mapped[str | None] = mapped_column(String)
    context: Mapped[str] = mapped_column(String)
    row_order: Mapped[int] = mapped_column(Integer, default=0)
    news_id: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String, default="pending")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvaluationLabel(Base):
    __tablename__ = "evaluation_labels"
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class ImportRow(Base):
    __tablename__ = "import_rows"
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    request_hash: Mapped[str] = mapped_column(String, unique=True)
    result: Mapped[dict] = mapped_column(JSON)
    raw: Mapped[dict] = mapped_column(JSON)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    duration: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="pending")
    etag: Mapped[str | None] = mapped_column(String)
    modified: Mapped[str | None] = mapped_column(String)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    received_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    state: Mapped[str] = mapped_column(String, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now
    )
    error: Mapped[str | None] = mapped_column(String)


class WorkerPresence(Base):
    __tablename__ = "worker_presence"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revision: Mapped[str | None] = mapped_column(String)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    context: Mapped[str] = mapped_column(String, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    event_type: Mapped[str] = mapped_column(String)
    signature: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    priority: Mapped[float] = mapped_column(Float)
    historical_priority: Mapped[float] = mapped_column(Float)
    event_date: Mapped[str] = mapped_column(String)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    history: Mapped[list] = mapped_column(JSON)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("incident_id", "revision"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    revision: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    kind: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    context_hash: Mapped[str] = mapped_column(String)


class ConsumptionBudget(Base):
    __tablename__ = "consumption_budgets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_limit: Mapped[int | None] = mapped_column(Integer)
    requests_used: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_seconds: Mapped[int | None] = mapped_column(Integer)


class Grant(Base):
    __tablename__ = "grants"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    split: Mapped[str] = mapped_column(String)
    article_limit: Mapped[int | None] = mapped_column(Integer)
    used: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_id: Mapped[str | None] = mapped_column(ForeignKey("consumption_budgets.id"))


class ApiCall(Base):
    __tablename__ = "api_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    article_id: Mapped[str] = mapped_column(String)
    stage: Mapped[str] = mapped_column(String)
    attempt: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String)
    status: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    usage: Mapped[dict] = mapped_column(JSON)
    budget_id: Mapped[str | None] = mapped_column(ForeignKey("consumption_budgets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    csrf: Mapped[str] = mapped_column(String)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RequestCache(Base):
    __tablename__ = "request_cache"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GrantArticle(Base):
    __tablename__ = "grant_articles"
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    grant_id: Mapped[str] = mapped_column(ForeignKey("grants.id"))
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
