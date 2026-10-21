# Planes de acción y redacción con Claude

Integra en esta app la parte de alertas y toma de decisión de la versión 3 de Lucas (`lucasmirlo/MAVERICKS-G12`, rama `sprint3`): planes de acción por incidente y borradores redactados por un modelo de lenguaje. En la v3 el modelo era local (Ollama `qwen3.5:9b`); aquí todo el trabajo de LLM va por la API de Anthropic.

## Qué decide cada parte

| Parte | Decide | No decide |
| --- | --- | --- |
| Perfil final congelado (JEV `decision-3.4.2`, revisión `review-1.3.1`) | Asociación, riesgo, urgencia, prioridad, alertas y exportación | — |
| Revisión humana (`human_decisions`, `incident_work`) | Decisiones operativas y seguimiento | — |
| Reglas del plan (`app/action_plans.py`, `acciones-1.0.0`) | Qué acciones sugerir y con qué plazo (hoy, esta semana, próximo informe) | Nada de lo anterior |
| Claude (`app/llm.py`) | Solo el texto: resumen del plan y reescritura de borradores | Ninguna clasificación, cifra ni acción |

El LLM **opina, no decide**: ninguna salida de Claude cambia `analyses`, `incidents`, `alerts`, la exportación ni las métricas del perfil final.

## Plan sugerido

- Tras cada análisis terminado, el worker encola con la prioridad más baja (0) un trabajo `action_plan` por cada incidente abierto que cite la noticia. Clave idempotente `plan:<incidente>:<revisión>`.
- `build_facts` saca todas las cifras de la base de datos: proveedor, inventario, lead time, productos, alternativo y si el alternativo tiene a su vez un incidente abierto.
- `choose_actions` aplica reglas explícitas:
  - **Vigilar** si no es urgente.
  - **Contactar al proveedor** siempre.
  - **Preparar el alternativo** si existe y no está afectado.
  - **Subir stock de seguridad** si el proveedor es físico y el caso es urgente, la duración es desconocida o supera la mitad de la cobertura.
  - **Segunda fuente** si es fuente única de criticidad alta, con urgencia o con evento prolongado.
  - **Cambiar ruta** si es un proveedor logístico.
  - **Verificar el vínculo** si la exposición es `potential` o p_vínculo < 0,65.
  - **Avisar a planificación** si es urgente y la parada supera la cobertura, o si es fuente única con duración desconocida.
- Plantilla determinista siempre disponible. Claude redacta un resumen de 80–120 palabras; se descarta si añade cifras ausentes de los hechos, si se sale de 50–160 palabras o si la llamada falla. El motivo queda en `summary_error`.
- En la ficha del proveedor, **Usar en el seguimiento** copia la acción y su fecha al formulario de `IncidentWorkspace`. No guarda nada: el presentador registra el seguimiento.
- Tabla `action_plans` (migración `0011`), una fila por incidente y revisión. `/readyz` y el worker exigen ahora el esquema `0011`.

## Borradores con Claude

La casilla **Redactar con Claude** de la ficha envía `assist: true` a `POST /api/drafts`. Claude reescribe la plantilla de `app/drafts.py` en el idioma del destinatario: español para países hispanohablantes, inglés para el resto. Conserva las preguntas y las advertencias («no constituye un pedido», sin confirmación de stock). Si añade cifras que no estaban en la plantilla, o si falla, se guarda la plantilla y la interfaz lo indica. El borrador guarda en `evidence_snapshot.writer` quién lo redactó, con modelo, latencia y tokens.

## Llamada a la API

- SDK oficial `anthropic==1.17.0`. `client.beta.messages.create` con:
  - modelo `ANTHROPIC_MODEL` (por defecto `claude-sonnet-5-5`);
  - `output_config.effort` (`ANTHROPIC_EFFORT`, por defecto `low`);
  - salida JSON con esquema estricto `{"texto": ...}`.
- Fallback de servidor activado (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`): si los clasificadores de seguridad rechazan una petición, Anthropic la reintenta con el modelo que recomienda para esa categoría.
- Un `stop_reason: "refusal"` restante, un error HTTP, un timeout (`LLM_TIMEOUT_SECONDS`, 25 s) o un límite de uso se convierten en `LLMError` y se conserva la plantilla.
- Los logs registran modelo, latencia y tokens; nunca el prompt, la respuesta ni la clave.
- El texto de la noticia se envía entre marcas `<<<DATOS>>>` y se declara como datos, no como instrucciones.

## Variables

| Variable | Valor |
| --- | --- |
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic. Solo en `.env` local o en las variables de Railway (web **y** worker). |
| `ANTHROPIC_WORKSPACE_ID` | Solo si la clave no pertenece a un workspace: la API exige entonces la cabecera `anthropic-workspace-id`. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` |
| `ANTHROPIC_EFFORT` | `low` |
| `LLM_PROVIDER` | `anthropic`; `none` desactiva Claude y deja solo plantillas |
| `LLM_TIMEOUT_SECONDS` | `25` |

Sin `ANTHROPIC_API_KEY` la app funciona igual, con plantillas.

## Pruebas

`tests/unit/test_action_plans.py` cubre:

- reglas del plan y control de cifras inventadas;
- uso del resumen de Claude solo cuando respeta los hechos, y plantilla ante cualquier fallo;
- forma de la petición a Anthropic (salida estructurada y fallback por defecto) y rechazo `refusal`;
- idioma y control de cifras de los borradores;
- plan idempotente por revisión que no modifica el incidente;
- trabajo encolado con prioridad 0.

Usa un proveedor falso: sin red ni clave.
