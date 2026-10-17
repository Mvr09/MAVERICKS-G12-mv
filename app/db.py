import ipaddress
import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.settings import settings


class DatabaseConfigurationError(RuntimeError):
    pass


def database_configuration_issue(database_url=None, railway=None):
    if railway is None:
        railway = any(
            os.environ.get(k)
            for k in (
                "RAILWAY_ENVIRONMENT_ID",
                "RAILWAY_PROJECT_ID",
                "RAILWAY_GIT_COMMIT_SHA",
            )
        )
    if not railway:
        return None
    host = make_url(database_url or settings.database_url).host
    loopback = not host or host.lower() in ("localhost", "localhost.localdomain")
    try:
        loopback = loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if loopback:
        return "DATABASE_URL debe referenciar PostgreSQL remoto en Railway; localhost no es una base de datos remota."
    return None


url = settings.database_url.replace("postgres://", "postgresql+psycopg://", 1)
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url, pool_pre_ping=True)


@event.listens_for(engine, "do_connect")
def validate_database_target(dialect, connection_record, cargs, cparams):
    issue = database_configuration_issue()
    if issue:
        raise DatabaseConfigurationError(issue)


Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    issue = database_configuration_issue()
    if issue:
        raise DatabaseConfigurationError(issue)
    with Session() as db:
        yield db
