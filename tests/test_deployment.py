"""Deployment checks without database or paid network requests."""

import json
import os
from pathlib import Path
from unittest.mock import patch
from app import web


def test_entrypoint_uses_the_domain_target_port():
    with patch.dict(os.environ, {"PORT": "12345"}), patch("app.web.uvicorn.run") as run:
        web.main()
    run.assert_called_once_with("app.main:app", host="0.0.0.0", port=8000)


def test_railway_default_and_explicit_web_config_agree():
    configs = [
        json.loads(Path(p).read_text())
        for p in ("railway.json", "railway.web.json", "config/railway.web.json")
    ]
    assert configs[0] == configs[1] == configs[2]
    assert configs[0]["deploy"]["startCommand"] == "python -m app.web"
    assert configs[0]["deploy"]["preDeployCommand"] == [
        "alembic upgrade head",
        "python -m app.cli seed",
    ]
    assert configs[0]["deploy"]["healthcheckPath"] == "/readyz"
    worker = json.loads(Path("railway.worker.json").read_text())
    assert worker["deploy"]["startCommand"] == "python -m app.worker"
    docker = Path("Dockerfile").read_text()
    assert "EXPOSE 8000" in docker
    assert 'CMD ["python", "-m", "app.web"]' in docker
    assert "RSS_ANALYSIS_ENABLED=false" in docker
