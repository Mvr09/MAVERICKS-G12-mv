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
- Claude recibe también la **evidencia literal** de la noticia: la frase que guarda el análisis de JEV, hasta 600 caracteres.
- En la misma llamada, Claude escribe una **nota «cómo hacerlo»** por acción: una frase en infinitivo con qué preguntar o comprobar en este caso. Cada nota se valida por separado (código de acción existente, 4–40 palabras, sin cifras ausentes de los hechos). Si una no pasa, esa acción se queda solo con el motivo de su regla y el resumen se conserva.
- **Usar en el seguimiento** copia la acción y su fecha al formulario de `IncidentWorkspace`. No guarda nada: el presentador registra el seguimiento.
- Tabla `action_plans` (migración `0011`), una fila por incidente y revisión. `/readyz` y el worker exigen ahora el esquema `0011`.

## Dónde se ve (como en la v3)

| Pantalla | Qué muestra |
| --- | --- |
| Ficha del proveedor | Tarjeta **Plan de acción** por incidente abierto: plazo de cada acción (píldora roja «Hoy», ámbar «Esta semana», gris «Próximo informe semanal») y su motivo; margen de stock y rotura estimada, productos en juego y alternativo; resumen («Redactado por IA» si es de Claude); botones de correo del plan con su idioma, p. ej. «Correo al proveedor (EN)». |
| Resumen · mesa de atención | En cada tarjeta: «Urgente», «Decide: JEV/humano», criticidad y fuente única; el titular; **Siguiente acción** con las dos primeras acciones y su plazo; margen y productos; enlace «Ver plan completo y borradores». |
| Alertas | Desplegable **Plan de acción (N acciones)** en cada alerta vigente, abierto por defecto en las urgentes sin reconocer. |
| Al entrar, en cualquier página | **Banner de urgencias** en tres líneas: cuántos proveedores están en situación urgente y cuáles, acciones para hoy y para esta semana, y por dónde empezar. «Vamos a ver qué hacer» lo cierra y lleva a la mesa de atención; no vuelve a salir en esa sesión del navegador. Sale de los planes y no llama a Claude. |

La lectura (`GET /api/plans?context=…` y `GET /api/incidents/{id}/plan`) es pública y no escribe nada. Si no hay plan guardado, se calcula al vuelo con la plantilla. Una lectura de presentador guarda el plan y sus correos y encola el resumen de Claude.

## Correos del plan

Se generan con plantillas, sin Claude y sin coste, en el idioma del destinatario según el país del catálogo: español para países hispanohablantes, inglés para el resto. Nunca se traducen al idioma local (chino, hindi…), porque el comprador no podría revisarlos.

- **Correo al proveedor** si el plan incluye contactarle.
- **Verificar vínculo** si la exposición está sin confirmar.
- **Correo al alternativo** si hay alternativo sin incidente abierto.

Con revisión pendiente solo se prepara la verificación: B no consulta al proveedor sin evidencia validada. Un correo editado por el comprador no se sobrescribe. En el diálogo, **Mejorar con Claude** (`POST /api/drafts/{id}/assist`) lo reescribe en el mismo idioma; si falla o añade cifras, el texto no cambia.

## Borradores con Claude

La casilla **Redactar con Claude** de la ficha envía `assist: true` a `POST /api/drafts`. Claude reescribe la plantilla de `app/drafts.py` en el idioma del destinatario: español para países hispanohablantes, inglés para el resto. Conserva las preguntas y las advertencias («no constituye un pedido», sin confirmación de stock). Si añade cifras que no estaban en la plantilla, o si falla, se guarda la plantilla y la interfaz lo indica. El borrador guarda en `evidence_snapshot.writer` quién lo redactó, con modelo, latencia y tokens.

## Llamada a la API

- SDK oficial `anthropic==1.17.0`. `client.beta.messages.create` con:
  - modelo `ANTHROPIC_MODEL` (por defecto `claude-sonnet-5-5`);
  - `output_config.effort` (`ANTHROPIC_EFFORT`, por defecto `low`);
  - salida JSON con esquema estricto `{"texto": ...}`.
- Fallback de servidor activado (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`): si los clasificadores de seguridad rechazan una petición, Anthropic la reintenta con el modelo que recomienda para esa categoría.
- Un `stop_reason: "refusal"` restante, un error HTTP, un timeout (`LLM_TIMEOUT_SECONDS`, 12 s, con un reintento) o un límite de uso se convierten en `LLMError` y se conserva la plantilla.
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
| `LLM_TIMEOUT_SECONDS` | `12`: con un reintento, una petición desde la web nunca pasa de los 30 s de `api.ts`. Una llamada real tarda unos 6–7 s. |

Sin `ANTHROPIC_API_KEY` la app funciona igual, con plantillas.

## Pruebas

`tests/unit/test_action_plans.py` cubre:

- reglas del plan y control de cifras inventadas;
- uso del resumen de Claude solo cuando respeta los hechos, y plantilla ante cualquier fallo;
- forma de la petición a Anthropic (salida estructurada y fallback por defecto) y rechazo `refusal`;
- idioma y control de cifras de los borradores;
- plan idempotente por revisión que no modifica el incidente;
- trabajo encolado con prioridad 0;
- correos del plan por idioma, que se crean una vez y no pisan textos editados;
- solo verificación con revisión pendiente;
- lectura pública sin escrituras.

Usa un proveedor falso: sin red ni clave.
