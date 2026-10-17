from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.main import app
from app.db import database_configuration_issue


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_railway_rejects_local_database_without_exposing_credentials(host):
    uri = f"postgresql+psycopg://user:PROTECTED_PASSWORD@{host}:5432/radar"
    issue = database_configuration_issue(uri, railway=True)
    assert issue and "PROTECTED_PASSWORD" not in issue
    assert database_configuration_issue(uri, railway=False) is None
    assert (
        database_configuration_issue(
            "postgresql+psycopg://user:PROTECTED_PASSWORD@postgres.railway.internal/radar",
            railway=True,
        )
        is None
    )


def test_invalid_remote_configuration_never_opens_a_connection(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "synthetic-test")
    with patch(
        "app.db.engine.connect",
        side_effect=AssertionError("No debe abrir conexiones a localhost"),
    ):
        with TestClient(app) as c:
            assert c.get("/healthz").status_code == 200
            for path in ["/readyz", "/api/suppliers", "/api/sources", "/api/session"]:
                response = c.get(path)
                assert response.status_code == 503
                assert response.json()["code"] == "DATABASE_CONFIGURATION"
                assert response.headers["retry-after"] == "30"


@pytest.mark.parametrize("schema", [False, True])
def test_database_failures_are_sanitized_and_do_not_escape_as_tracebacks(schema):
    original = Exception("PROTECTED_DATABASE_PASSWORD")
    original.sqlstate = "42P01" if schema else "08006"
    error = (ProgrammingError if schema else OperationalError)(
        "SELECT protected_sql", {"password": "PROTECTED_PARAMETER"}, original
    )
    with patch("app.main.suppliers_view", side_effect=error):
        response = TestClient(app).get("/api/suppliers")
    assert response.status_code == 503
    assert response.json()["code"] == (
        "DATABASE_SCHEMA_UNAVAILABLE" if schema else "DATABASE_UNAVAILABLE"
    )
    assert "PROTECTED" not in response.text and "SELECT" not in response.text
