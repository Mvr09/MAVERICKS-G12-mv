"""Reparación de nombres históricos: sin inferir por split ni sobrescribir cargas."""

from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.cli import seed
from app.db import Session
from app.main import app
from app.models import Batch, Article, Analysis, ApiCall
from app.views import batch_label


def test_historical_names_restored_by_content_without_overwriting_or_reanalysis():
    with Session() as db:
        validation = db.scalar(select(Batch).where(Batch.split == "validation"))
        custom = db.scalar(select(Batch).where(Batch.split == "test"))
        unknown = db.scalar(select(Batch).where(Batch.split == "liveday"))
        validation.filename = None
        custom.filename = "Nombre elegido por el usuario.xlsx"
        unknown.filename = None
        unknown.file_hash = "MOCK-UNRECOGNIZED-CONTENT"
        db.commit()
        counts = [
            db.scalar(select(func.count()).select_from(model))
            for model in [Batch, Article, Analysis, ApiCall]
        ]
        seed(db)
        db.commit()
        seed(db)
        db.commit()
        db.refresh(validation)
        db.refresh(custom)
        db.refresh(unknown)
        assert validation.filename == "supplier_validation.xlsx"
        assert custom.filename == "Nombre elegido por el usuario.xlsx"
        assert unknown.filename is None
        assert unknown.id[:8] not in batch_label(unknown)
        assert "no registrado" in batch_label(unknown)
        assert counts == [
            db.scalar(select(func.count()).select_from(model))
            for model in [Batch, Article, Analysis, ApiCall]
        ]
        bid = validation.id
    with TestClient(app) as c:
        batches = c.get("/api/batches").json()
        restored = next(b for b in batches if b["id"] == bid)
        assert (
            restored["filename"]
            == restored["origin_label"]
            == "supplier_validation.xlsx"
        )
        article = c.get("/api/articles?context=exercise&origin=batch:" + bid).json()[0]
        assert article["origin_label"] == "supplier_validation.xlsx"
