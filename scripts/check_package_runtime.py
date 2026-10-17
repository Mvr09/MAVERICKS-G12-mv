"""Smoke test the packaged filesystem layout. This is NOT a Docker build."""

from pathlib import Path
import tempfile, shutil, subprocess, sys, os, json

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="radar-package-") as directory:
    target = Path(directory)
    shutil.copytree(ROOT / ".runtime/deploy", target, dirs_exist_ok=True)
    shutil.copytree(ROOT / "frontend/dist", target / "frontend/dist")
    code = """from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings
c=TestClient(app)
assert c.get('/readyz').status_code==200
assert c.get('/').status_code==200
assert c.get('/api/suppliers').json()['total']==40
assert c.get('/.env').status_code==404
assert c.post('/api/sources/sync').status_code==401
assert not settings.typesafe_api_key.get_secret_value()
print('Runtime empaquetado: pasa; sin .env ni secretos en el paquete')
"""
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=target,
        check=True,
        env={
            k: v
            for k, v in os.environ.items()
            if k.upper() not in ("TYPESAFE_API_KEY", "ADMIN_PASSWORD", "SESSION_SECRET")
        },
    )
report = {
    "filesystem_runtime": "passes",
    "docker_build": "not executed: Docker unavailable",
    "secrets_in_package": False,
}
(ROOT / "reports/package-runtime.json").write_text(json.dumps(report, indent=2))
