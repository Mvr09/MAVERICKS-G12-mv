"""One Railway command: migrations must succeed before idempotent initialization."""

from alembic import command
from alembic.config import Config
from app.settings import ROOT


def main():
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    from app.cli import seed
    from app.db import Session

    with Session() as db:
        seed(db)
        db.commit()
    print("Migraciones e inicialización de fuentes y cupos completadas.")


if __name__ == "__main__":
    main()
