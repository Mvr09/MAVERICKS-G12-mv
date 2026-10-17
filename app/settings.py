from pathlib import Path
import json
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'config/risk_policy.json').read_text())
RSS = json.loads((ROOT / 'config/rss_sources.json').read_text())

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore', case_sensitive=False)
    database_url: str = 'postgresql+psycopg://radar:radar@localhost:5432/radar'
    typesafe_api_key: SecretStr = SecretStr('')
    admin_password: SecretStr = SecretStr('')
    session_secret: SecretStr = SecretStr('')
    jev_model: str = POLICY['default_model']
    app_base_url: str = 'http://localhost:8000'
    # Paid inference is fail-closed; a grant must be explicitly created by CLI.
    rss_analysis_enabled: bool = False
    max_upload_bytes: int = 10_000_000
    max_import_rows: int = 5000

    def credential_status(self):
        return {k.upper(): 'configurada' if getattr(self, k).get_secret_value().strip() else 'faltante'
                for k in ('typesafe_api_key', 'admin_password', 'session_secret')}

settings = Settings()
