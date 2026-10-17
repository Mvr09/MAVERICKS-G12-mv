"""Prepare only the disposable radar_test database, with explicitly mocked decisions."""

import json
from pathlib import Path
from sqlalchemy.engine import make_url
from openpyxl import Workbook
import httpx
from app.db import Base, engine, Session
from app.cli import seed
from app.importer import import_excel
from app.analysis import process_article
from tests.helpers import synthetic, answer

if make_url(str(engine.url)).database != "radar_test":
    raise SystemExit("Base de E2E debe ser radar_test")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
with engine.begin() as c:
    c.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS alembic_version(version_num varchar(32) primary key)"
    )
    c.exec_driver_sql("DELETE FROM alembic_version")
    c.exec_driver_sql("INSERT INTO alembic_version VALUES ('0002')")
with Session() as db:
    seed(db)
    import_excel(
        db, Path("inputs/supplier_training.xlsx").read_bytes(), "training.xlsx"
    )
    db.commit()
    a = synthetic(
        db,
        headline="MOCK IDENTIFICADO: interrupción sintética para pruebas de interfaz",
    )
    process_article(
        db,
        a.id,
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, json=answer(json.loads(r.content), linked=("S001",))
            )
        ),
    )
output = Path(".runtime/e2e-upload.xlsx")
output.parent.mkdir(exist_ok=True)
w = Workbook()
s = w.active
s.title = "News"
s.append(["News_ID", "Published_Date", "Source", "Headline", "Summary"])
s.append(
    [
        "SYNTHETIC-UPLOAD",
        "2026-10-17",
        "MOCK IDENTIFICADO",
        "Noticia sintética de carga",
        "Solo prueba de importación, sin inferencia.",
    ]
)
w.save(output)
print("E2E preparado con mocks identificados; ninguna llamada real a JEV")
