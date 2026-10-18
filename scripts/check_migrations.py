"""Verify frozen Alembic revisions on a separate, non-demo database."""

import os, subprocess, sys, json
import psycopg
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from app.db import Base
from app import models
from app.settings import settings

url = make_url(settings.database_url)
with psycopg.connect(
    host=url.host,
    port=url.port,
    user=url.username,
    password=url.password,
    dbname="postgres",
    autocommit=True,
) as c:
    if not c.execute(
        "SELECT 1 FROM pg_database WHERE datname='radar_migration_test_v2'"
    ).fetchone():
        c.execute("CREATE DATABASE radar_migration_test_v2")
target = url.set(database="radar_migration_test_v2")
env = dict(os.environ)
env["DATABASE_URL"] = target.render_as_string(hide_password=False)
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True
)
engine = create_engine(target)
assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {
    "alembic_version"
}
print(
    json.dumps(
        {
            "migrations": "passes",
            "database": "radar_migration_test_v2",
            "tables": len(Base.metadata.tables),
            "revision": "0008",
        }
    )
)
