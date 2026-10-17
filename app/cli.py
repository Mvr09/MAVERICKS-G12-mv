"""Explicit local operations; never walks directories for datasets."""

import argparse, json
from pathlib import Path
from sqlalchemy import select, text
from app.db import Session
from app.models import Source, Grant, ConsumptionBudget
from app.settings import ROOT, RSS, settings
from app.importer import import_excel


def seed(db):
    db.execute(text("SELECT pg_advisory_xact_lock(72642, 2)"))
    authorization = json.loads((ROOT / "config/authorization.json").read_text())
    for budget in authorization.get("request_budgets", []):
        if not db.get(ConsumptionBudget, budget["id"]):
            db.add(
                ConsumptionBudget(
                    id=budget["id"],
                    request_limit=budget["request_limit"],
                    requests_used=0,
                    window_seconds=budget["window_seconds"],
                )
            )
    db.flush()
    for source in RSS["sources"]:
        if not db.get(Source, source["id"]):
            db.add(Source(id=source["id"], data=source))
    if not db.get(Grant, "initial-training-3"):
        db.add(
            Grant(
                id="initial-training-3",
                split="training",
                article_limit=authorization["initial_training_limit"],
                used=authorization["initial_training_consumed"],
            )
        )
    for grant in authorization.get("additional_grants", []):
        if not db.get(Grant, grant["id"]):
            from datetime import datetime

            db.add(
                Grant(
                    id=grant["id"],
                    split=grant["split"],
                    article_limit=grant["article_limit"],
                    used=0,
                    budget_id=grant.get("budget_id"),
                    expires_at=datetime.fromisoformat(
                        grant["expires_at"].replace("Z", "+00:00")
                    ),
                )
            )


def main():
    parser = argparse.ArgumentParser(description="Operaciones Supplier Risk Radar")
    parser.add_argument(
        "command", choices=["config", "import-manifest", "seed", "grant", "sync"]
    )
    parser.add_argument("--id")
    parser.add_argument(
        "--split", choices=["training", "validation", "test", "liveday", "rss"]
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--expires-at")
    args = parser.parse_args()
    if args.command == "config":
        print(json.dumps(settings.credential_status(), ensure_ascii=False))
        return
    with Session() as db:
        if args.command in ("seed", "import-manifest"):
            seed(db)
        if args.command == "import-manifest":
            manifest = json.loads((ROOT / "evidence/input_manifest.json").read_text())
            for entry in manifest["files"]:
                path = ROOT / entry["path"]
                if path.suffix == ".xlsx":
                    b, d = import_excel(db, path.read_bytes(), path.name)
                    print(json.dumps({"batch_id": b.id, **d}, ensure_ascii=False))
        if args.command == "grant":
            from datetime import datetime

            if (
                not args.id
                or not args.split
                or not args.limit
                or args.limit < 1
                or not args.expires_at
            ):
                parser.error(
                    "Grant requiere --id, --split, --limit y --expires-at con zona UTC"
                )
            expiry = datetime.fromisoformat(args.expires_at.replace("Z", "+00:00"))
            if not expiry.tzinfo:
                parser.error("expires-at requiere zona horaria")
            if db.get(Grant, args.id):
                parser.error("El grant ya existe; no se reinicia su consumo")
            db.add(
                Grant(
                    id=args.id,
                    split=args.split,
                    article_limit=args.limit,
                    expires_at=expiry,
                )
            )
        if args.command == "sync":
            from app.queue import enqueue_sync

            print(enqueue_sync(db))
        db.commit()


if __name__ == "__main__":
    main()
