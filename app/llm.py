"""Redacción con Claude (API de Anthropic). Solo redacta texto a partir de hechos ya calculados:
nunca decide asociación, riesgo, urgencia, prioridad ni exportación. Cualquier fallo devuelve
LLMError y quien llama conserva su plantilla.

Variables: LLM_PROVIDER (anthropic | none), ANTHROPIC_API_KEY, ANTHROPIC_WORKSPACE_ID (solo claves sin
workspace), ANTHROPIC_MODEL (claude-sonnet-5-5), ANTHROPIC_EFFORT (low), LLM_TIMEOUT_SECONDS, LLM_MAX_TOKENS.
La clave solo vive en el entorno."""
import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict

from app.settings import settings

log = logging.getLogger("radar.llm")
# Fallback de servidor ante un rechazo de seguridad: Anthropic elige el modelo según la categoría.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_lock = threading.Lock()
_provider = None


class LLMError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code  # disabled | auth | rate_limit | timeout | unavailable | http_error | refusal | invalid_output
        self.message = message


@dataclass
class CallRecord:
    provider: str
    model: str
    purpose: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    served_by: str | None = None
    request_id: str | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self):
        out = asdict(self)
        out.update(out.pop("extra"))
        return out


TEXT_SCHEMA = {
    "type": "object",
    "properties": {"texto": {"type": "string"}},
    "required": ["texto"],
    "additionalProperties": False,
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key, model, effort, timeout, max_tokens, workspace_id=""):
        import anthropic

        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._anthropic = anthropic
        headers = {"anthropic-workspace-id": workspace_id} if workspace_id else None
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1, default_headers=headers)

    def complete(self, system, user, schema):
        a = self._anthropic
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except a.AuthenticationError as exc:
            raise LLMError("auth", "Clave de Anthropic no válida o sin permisos.") from exc
        except a.PermissionDeniedError as exc:
            raise LLMError("auth", "La clave de Anthropic no tiene acceso a este modelo.") from exc
        except a.RateLimitError as exc:
            raise LLMError("rate_limit", "Límite de uso de Anthropic alcanzado; se reintentará más tarde.") from exc
        except a.APITimeoutError as exc:
            raise LLMError("timeout", "Claude no respondió a tiempo.") from exc
        except a.APIConnectionError as exc:
            raise LLMError("unavailable", "No se pudo conectar con la API de Anthropic.") from exc
        except a.BadRequestError as exc:
            hint = " La clave no tiene workspace: define ANTHROPIC_WORKSPACE_ID." if "workspace" in str(exc.message) else ""
            raise LLMError("http_error", "La API de Anthropic rechazó la petición (HTTP 400)." + hint) from exc
        except a.APIStatusError as exc:
            raise LLMError("http_error", f"La API de Anthropic devolvió HTTP {exc.status_code}.") from exc
        if response.stop_reason == "refusal":
            category = getattr(getattr(response, "stop_details", None), "category", None)
            raise LLMError("refusal", f"Claude rechazó la petición ({category or 'sin categoría'}).")
        if response.stop_reason == "max_tokens":
            raise LLMError("invalid_output", "La respuesta de Claude quedó cortada.")
        text = next((b.text for b in response.content if b.type == "text"), "")
        usage = response.usage
        return text, {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "served_by": response.model,
            "request_id": getattr(response, "_request_id", None),
        }


class FakeProvider:
    """Solo pruebas: `responder(system, user)` devuelve el texto JSON o lanza LLMError."""
    name = "fake"
    model = "fake-model"

    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def complete(self, system, user, schema):
        self.calls.append((system, user))
        return self.responder(system, user), {"input_tokens": len(user) // 4, "output_tokens": 50, "served_by": self.model}


def get_provider():
    global _provider
    with _lock:
        if _provider is None and settings.llm_provider == "anthropic":
            key = settings.anthropic_api_key.get_secret_value().strip()
            if key:
                _provider = AnthropicProvider(key, settings.anthropic_model, settings.anthropic_effort,
                                              settings.llm_timeout_seconds, settings.llm_max_tokens,
                                              settings.anthropic_workspace_id.strip())
        return _provider


def set_provider(provider):
    """Solo pruebas: fija un proveedor (p. ej. FakeProvider) o lo reconstruye desde el entorno con None."""
    global _provider
    with _lock:
        _provider = provider


def status():
    """Sin secretos: solo si hay clave y qué modelo se usaría."""
    configured = settings.llm_provider == "anthropic" and bool(settings.anthropic_api_key.get_secret_value().strip())
    p = _provider
    return {
        "provider": p.name if p else settings.llm_provider,
        "model": p.model if p else settings.anthropic_model,
        "configured": configured or p is not None,
        "role": "Redacta planes y borradores; no decide riesgo, urgencia ni prioridad.",
    }


def wrap(tag, payload):
    return f"<<<{tag}>>>\n{json.dumps(payload, ensure_ascii=False, default=str)}\n<<<FIN_{tag}>>>"


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "texto": {"type": "string"},
        "acciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"codigo": {"type": "string"}, "nota": {"type": "string"}},
                "required": ["codigo", "nota"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["texto", "acciones"],
    "additionalProperties": False,
}


def write_json(system, user, schema, *, purpose, min_chars=20, max_chars=4000):
    """JSON redactado por Claude con un campo "texto" obligatorio; lanza LLMError si no hay respuesta válida."""
    provider = get_provider()
    if provider is None:
        raise LLMError("disabled", "Claude no está configurado (falta ANTHROPIC_API_KEY o LLM_PROVIDER=none).")
    t0 = time.monotonic()
    raw, meta = provider.complete(system, user, schema)
    try:
        data = json.loads(raw)
        data["texto"] = str(data["texto"]).strip()
    except (ValueError, KeyError, TypeError) as exc:
        raise LLMError("invalid_output", "La respuesta de Claude no era el JSON esperado.") from exc
    if not min_chars <= len(data["texto"]) <= max_chars:
        raise LLMError("invalid_output", f"La respuesta de Claude tenía {len(data['texto'])} caracteres.")
    rec = CallRecord(provider.name, provider.model, purpose, int((time.monotonic() - t0) * 1000),
                     meta.get("input_tokens"), meta.get("output_tokens"), meta.get("served_by"), meta.get("request_id"))
    # Nunca se registran prompts, respuestas ni credenciales.
    log.info("llm call provider=%s model=%s served_by=%s purpose=%s latency_ms=%s in=%s out=%s",
             rec.provider, rec.model, rec.served_by, purpose, rec.latency_ms, rec.input_tokens, rec.output_tokens)
    return data, rec


def write_text(system, user, *, purpose, min_chars=20, max_chars=4000):
    """Texto redactado por Claude como JSON {"texto": ...}; lanza LLMError si no hay respuesta válida."""
    data, rec = write_json(system, user, TEXT_SCHEMA, purpose=purpose, min_chars=min_chars, max_chars=max_chars)
    return data["texto"], rec
