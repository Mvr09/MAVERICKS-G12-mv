"""Build an allowlisted Railway upload directory; excludes kit inputs and secrets."""

from pathlib import Path
import shutil, tarfile, json
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".runtime/deploy"
# Only generated deployment staging is replaced. Never touch inputs or persistence.
if TARGET.exists():
    shutil.rmtree(TARGET)
TARGET.mkdir(parents=True)
files = [
    "Dockerfile",
    ".dockerignore",
    ".env.example",
    "requirements.lock",
    "alembic.ini",
    "railway.json",
    "railway.web.json",
    "railway.worker.json",
    "README.md",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "reference/jev_requests.py",
    "reference/scoring.py",
    "config/risk_policy.json",
    "config/geography.json",
    "config/jev_transport.json",
    "config/rss_sources.json",
    "config/authorization.json",
]
for folder in ["app", "migrations", "contracts", "frontend/src"]:
    files.extend(
        str(p.relative_to(ROOT))
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
values = dotenv_values(ROOT / ".env")
secrets = [
    values.get(k)
    for k in ["TYPESAFE_API_KEY", "ADMIN_PASSWORD", "SESSION_SECRET"]
    if values.get(k)
]
for name in files:
    source = ROOT / name
    if not source.is_file():
        raise SystemExit("Falta artefacto requerido: " + name)
    content = source.read_bytes()
    if any(s.encode() in content for s in secrets):
        raise SystemExit("Revisión de secreto fallida: " + name)
    destination = TARGET / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
archive = ROOT / ".runtime/supplier-risk-radar-deploy.tar.gz"
with tarfile.open(archive, "w:gz") as tar:
    for name in sorted(files):
        tar.add(TARGET / name, arcname=name)
print(
    json.dumps(
        {
            "staging": str(TARGET),
            "archive": str(archive),
            "files": len(files),
            "original_datasets": False,
            "secrets": False,
        },
        ensure_ascii=False,
    )
)
