"""Actual RSS probe. Report provenance is local, never Railway."""

import json
from concurrent.futures import ThreadPoolExecutor
from app.db import Session
from app.settings import RSS, ROOT
from app.rss import sync_source
from app.models import now


def check(source):
    with Session() as db:
        result = sync_source(db, source["id"])
        db.commit()
        return {"source": source["id"], "checked_at": now().isoformat(), **result}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, RSS["sources"]))
    report = {
        "environment": "local development; not Railway",
        "checked_at": now().isoformat(),
        "sources": results,
    }
    (ROOT / "reports/rss-local.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
