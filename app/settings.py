from pathlib import Path
import json
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config/risk_policy.json").read_text())
RSS = json.loads((ROOT / "config/rss_sources.json").read_text())
AUTHORIZATION = json.loads((ROOT / "config/authorization.json").read_text())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="ignore", case_sensitive=False
    )
    database_url: str = "postgresql+psycopg://radar:radar@localhost:5432/radar"
    typesafe_api_key: SecretStr = SecretStr("")
    admin_password: SecretStr = SecretStr("")
    session_secret: SecretStr = SecretStr("")
    jev_model: str = POLICY["default_model"]
    app_base_url: str = "http://localhost:8000"
    # Grants keep durable accounting; the user disabled local budget enforcement.
    jev_budget_limits_enabled: bool = AUTHORIZATION["budget_limits_enabled"]
    rss_analysis_enabled: bool = False
    demo_fixtures_enabled: bool = False
    max_upload_bytes: int = 10_000_000
    max_import_rows: int = 5000
    # Redacción con Claude (planes de acción y borradores). Nunca decide riesgo,
    # urgencia ni prioridad. Sin clave o con LLM_PROVIDER=none se usa la plantilla.
    llm_provider: str = "anthropic"
    anthropic_api_key: SecretStr = SecretStr("")
    # Solo para claves sin workspace asignado: la API exige la cabecera anthropic-workspace-id.
    anthropic_workspace_id: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_effort: str = "low"
    # api.ts aborts at 30 s: 12 s x 2 attempts plus backoff stays below it.
    llm_timeout_seconds: float = 12.0
    llm_max_tokens: int = 4000

    @field_validator("database_url", mode="before")
    @classmethod
    def local_database_default(cls, value):
        return value or "postgresql+psycopg://radar:radar@localhost:5432/radar"

    def credential_status(self):
        return {
            k.upper(): "configurada"
            if getattr(self, k).get_secret_value().strip()
            else "faltante"
            for k in ("typesafe_api_key", "admin_password", "session_secret")
        }


settings = Settings()
