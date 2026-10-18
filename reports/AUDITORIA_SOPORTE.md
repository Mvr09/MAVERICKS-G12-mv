# Auditoría de soporte, exposición y revisión

## Alcance y evidencia

Se conservan **1.0.0 predeterminado** y **link-2.2.0 experimental**. El ensayo factorial queda aplazado. Solo se reutilizaron training/sintéticos y las respuestas ya almacenadas; no se consultaron validation, test ni LiveDay. No hubo nuevas llamadas JEV ni modificaciones de preguntas, política, composición del vínculo o bloqueo de revisión.

Se reconstruyó exactamente el payload B cacheado de la interrupción parcial usando las preguntas actuales y sus candidatos originales. `validate_response` acepta la respuesta guardada contra ese payload. En los 36 resultados almacenados se comprobaron **126 respuestas de soporte**: todas son `type=noul`, con campo `noul` numérico en [0,1]. Las huellas de los seis archivos congelados del perfil permanecen iguales. Los resultados de ese control no equivalen a nueva precisión medida.

Evidencia privada: `reports/private/link-cached-scope-diagnosis.json` contiene payload efectivo y respuesta originales de B; `link-support-audit.json` contiene las respuestas A/B de los 36 casos. Las referencias por noticia siguen fuera de Git/Docker. Ningún secreto forma parte de estos documentos.

## 1. Preguntas exactas y mapeo

`scope_and_link_evidence` y `risk_evidence` son identificadores del **campo de diagnóstico** emitido por `app/link_analysis.py`, no preguntas del wire/API. No debe buscarse una respuesta JEV con esos nombres.

| Campo del diagnóstico | Pregunta JEV | Lectura en el código |
|---|---|---|
| scope_and_link_evidence | association_support_<supplier_id> | answers[...].noul |
| risk_evidence | risk_support_<supplier_id> | answers[...].noul |

Texto exacto de `association_support`, con supplier/geography específicos adjuntos en `instructions`:

> Does the article plus the supplied catalog/geographic facts provide sufficient evidence to establish or clearly exclude a relationship to this supplier? A different named organisation, unrelated activity, or expressly unaffected area can support exclusion. Missing or conflicting location/operational facts are insufficient. Do not use a conditional risk answer as evidence of association.

Texto exacto de `risk_support`, con el mismo contexto adjunto:

> Does the article provide sufficient facts to decide whether this supplier's supply faces a threat or not? An explicit positive development or clearly harmless event supports a negative decision. Missing operational information or unsupported speculation is insufficient. Association alone does not establish risk.

Ambas son proposiciones sobre **suficiencia de soporte para decidir**, no sobre si el vínculo/riesgo es positivo. Un Noul alto puede respaldar una conclusión positiva o una negativa. Un Noul bajo significa soporte insuficiente; **no** significa exclusión respaldada ni ausencia de riesgo. Las respuestas de identidad, área, operación y riesgo deciden la dirección por separado.

### Noticia y catálogo

- Asociación admite expresamente combinar noticia, catálogo y geografía. La relación puede proceder de identidad explícita o de área afectada más compatibilidad operativa. Los alias y regiones verifican lugares, no instalaciones del proveedor.
- Riesgo pregunta por hechos del artículo, contextualizados con `instructions.supplier`, `instructions.geography` y `state.suppliers`. El catálogo puede identificar el objeto expuesto; no aporta por sí solo un hecho de interrupción, pérdida, ruta o daño. No hay instrucción que permita completar hechos empresariales ausentes.
- Un nombre diferente puede excluir identidad y todavía dejar exposición regional posible. Esa diferencia de nombre solo no prueba exclusión de toda relación operativa. Una cita inofensiva y una actividad incompatible, o un área expresamente no afectada con ubicación conocida, sí pueden respaldarla.
- La frase de soporte reúne establecer/excluir en una sola pregunta: no revela qué rama está respaldada. Es una limitación de diagnóstico, no prueba de polaridad invertida. Los datos cacheados no permiten demostrar que dividirla mejore el clasificador; no se modifica ahora.

### Citas y puertas del código

`link_evidence_<id>` pregunta:

> Which article passage best supports the identity, operational scope, or exclusion of this supplier? Choose none when no passage is sufficient. Several passages may be valid.

`evidence_<id>` pregunta:

> Which passage best supports supply risk or its absence? A positive or harmless fact can support a negative judgment. Choose none if insufficient. Several passages may be valid.

Son Choice con citas literales y opción `none`. **Seleccionar una cita no prueba la conclusión.** El código exige, además:

- Asociación/exclusión: `association_support.noul > review_high` **y** `link_evidence.choice != none`; se comprueba también para candidatos no aceptados.
- Riesgo: cuando el proveedor supera la puerta de vínculo, `risk_support.noul > review_high` **y** `evidence.choice != none`, tanto para riesgo positivo como negativo.
- Una Choice difusa entre varias citas válidas se registra como observación auxiliar. Esa confianza nunca sustituye el Noul de soporte. Una cita `none` sigue siendo bloqueo cuando corresponde, incluso si el Noul es alto.
- El vínculo sigue siendo `max(identidad, min(área, operación))`, separado del riesgo condicionado; riesgo y urgencia conservan sus puertas. Un candidato descartado con soporte insuficiente permanece en revisión.

### Umbral y conclusión

`review_high=0,65` procede de `config/risk_policy.json` (política inicial no calibrada) y del límite superior inclusivo de su zona de ambigüedad [0,35;0,65]. Pedir soporte **estrictamente superior** conserva una decisión afirmativa fuera de esa zona. No deriva de sensibilidad/especificidad medida para estas preguntas de soporte, ni garantiza un 65 % de corrección. La frontera 0,65/0,6501 se prueba explícitamente; no se rebaja.

**No se encontró un defecto verificable de contrato, selección de campo o polaridad.** El payload y las respuestas guardadas son compatibles con las lecturas del normalizador. La ambigüedad de la palabra «relación» y el juicio conjunto establecer/excluir merecen estudio posterior, pero no justifican retirar bloqueos ahora. Las 46 evaluaciones de asociación y 16 de riesgo con soporte insuficiente en training tienen realmente Noul bajo; la UI no convirtió una confianza Choice en ese valor. Por eso no se cambian las preguntas ni la revisión para mejorar métricas.

## 2. Soporte factual, compatibilidad e incertidumbre

| Concepto | Representación actual | Qué permite afirmar |
|---|---|---|
| Hecho de la fuente | spans literales `evidence`, con campo y offsets | «La noticia dice…»; no verifica por sí solo que la empresa simulada tenga una planta o una ruta. |
| Hecho del catálogo | ciudad/país/material declarados; snapshot geográfico con procedencia | «El catálogo sitúa/describe…». Un lugar enriquecido no es un dato empresarial nuevo. |
| Compatibilidad | p_identity, área/operación en respuesta cruda; p_exposure=min(área,operación) | Señales de identidad o compatibilidad de exposición. No son porcentajes calibrados de afectación física. |
| Hipótesis explícita | interpretación de exposición potencial por operación compatible y zona, con hechos citados | Permite priorizar comprobación; no inventa instalación, ruta, provincia o daño. Si falta un dato relevante, se marca como desconocido y se conserva revisión. |
| Asociación sustentada | association_status=confirmed, cuando no hay bloqueo de asociación | El vínculo pasa las reglas actuales. No confirma afectación individual; otros campos aún pueden requerir revisión. |
| Exclusión sustentada | association_status=excluded, con soporte y cita | Hay soporte suficiente para excluir la relación según los datos disponibles. p_link bajo por sí solo no basta. |
| Asociación incierta | association_status=review y review_details | Falta soporte o hay ambigüedad relevante; no se presenta como exclusión demostrada. |
| Afectación reportada de una entidad | afirmación literal atribuida a la fuente, identidad y alcance respaldados | Solo puede describirse como reportada, distinguiendo qué instalación/actividad menciona la noticia. |
| Afectación confirmada | **no existe actualmente un campo de verificación empresarial/humana** | No se infiere de association_status, is_risk, impact_status=active, una cita o un Noul alto. Requeriría registrar verificación explícita, procedencia, fecha y hechos de identidad/instalación pertinentes. |

La ficha cambia «Asociación final: Confirmada» por «Sustentada», e identifica identidad/exposición como señales. Explica que no confirma afectación individual ni embarques de Helixa. Es una aclaración de representación, sin cambios de decisiones ni de datos. Las salidas históricas conservan sus campos y valores.

No se añaden plantas/rutas ni se resuelve una provincia con etiquetas esperadas. En el caso parcial, compatibilidad de operación baja y soporte bajo siguen siendo incertidumbre; el arreglo de duración no se presenta como solución de esa asociación.

## 3. Duración: cambio independiente

Commit independiente del extractor `duration-1.1.0`, reexportado por `app.analysis.durations`. Soporta cifras y números escritos del uno al doce en inglés/español, límites inferiores explícitos y texto literal. Mantiene la convención previa de 7 días/semana y 30 días/mes. Procesa cada campo por separado para no fabricar frases entre titular/resumen.

Periodos indefinidos, rangos, aproximaciones y fechas relativas probadas no se convierten en una duración fija. La lista de candidatos todavía no afirma duración de interrupción: JEV debe escoger la duración relevante o `unknown`. Se conserva `lower_bound` después de seleccionar el candidato. La generación de candidatos cambia el hash del payload B; no se reutiliza una respuesta antigua como si hubiera visto los candidatos nuevos. No se reescribe ningún resultado histórico.

## 4. Comprobación pequeña preparada, no ejecutada con JEV

El factorial queda aplazado: la auditoría no encontró un defecto que requiera otra versión de preguntas. La comprobación de consumo propuesta a continuación solo verifica el cambio de extracción y su selección, sin optimizar riesgo/proveedores/urgencia.

- **Seis noticias sintéticas**, tres pares semánticamente equivalentes: `two days`/`2 days`, `dos días`/`2 días`, `at least two days`/`at least 2 days`. Mismo evento industrial ficticio de Hangzhou y mismo catálogo completo (40 identidades); sin etiquetas ni hechos empresariales añadidos.
- **12 peticiones iniciales, hasta 36 HTTP con tres intentos por etapa**, sin reintentar respuestas válidas. Reutilizar A idéntica solo cuando su hash efectivo coincida; nunca reutilizar B antigua cuyo payload haya cambiado. Registrar modelo, uso, intentos, tiempo y caché. Parar ante 401/contrato y diagnosticar antes de insistir.
- Perfil experimental 2.2.0 y modelo fijado; sin preguntas nuevas. A selecciona candidatos de las 40 identidades; B se construye con los realmente seleccionados, no con un vínculo forzado ni un proveedor extraído de una referencia.
- Antes de ejecutar, congelar hashes de parser, preguntas, política y catálogo. Mantener este lote separado de los históricos. Esta comprobación **no** promociona el perfil ni ofrece una nueva evaluación independiente de precisión.
- Expectativa del parser: cita exacta, dos días y flag inferior correcto en los seis. Expectativa de B: seleccionar el candidato solo si juzga que la frase corresponde a la interrupción; `unknown` inesperado se registra como fallo de selección, no se corrige a mano. No forzar vínculo o riesgo para conseguir una duración. Conservar revisión si los otros campos carecen de soporte.
- Indefinidos y expresiones no utilizables ya se verifican localmente y no necesitan consumo. Cualquier diferencia de riesgo, proveedores, urgencia o revisión entre pares se registra, no se utiliza para ajustar preguntas.

La especificación reproducible de los seis casos queda en `reports/duration-directed-check.json`; las pruebas offline construyen los payloads con 40 proveedores sintéticos identificados. La ejecución autenticada posterior deberá usar la instantánea completa del catálogo real de la cartera simulada y conservar su procedencia. No hay runner de pago automático ni RSS periódico habilitado.

## 5. Pruebas ejecutadas y límites

- `python -m pytest tests/unit/test_durations.py -q`: 42 pruebas pasan en el commit independiente del parser; cubren los cuatro grupos solicitados, citas, mínimos y periodos no utilizables.
- `python -m pytest tests/unit -q`: 63 pasan (44 de duración/preparación y 19 de soporte/contrato), sin importar datasets ni conectar DB/API.
- Replay offline de los 36 resultados almacenados con sus candidatos de duración **originales**: mismas decisiones, proveedores, urgencia, revisiones y evaluaciones por proveedor. No mide la selección de los candidatos nuevos. Dos entradas de training y un sintético reciben nuevos candidatos con el parser corregido; detalle privado en `support-audit-replay.json`.
- Payload cacheado de B reconstruido exactamente; contrato validado y 126 campos Noul comprobados. Las huellas de los seis archivos congelados coinciden.
- `npm run build`: TypeScript y Vite pasan.
- Playwright local con APIs simuladas: 4/4 pasan a 360, 390, 768 y 1440 px; comprueba aclaración de exposición, revisión por campo, default1.0.0 y confirmación del perfil experimental.

No son pruebas autenticadas nuevas de JEV ni una nueva evaluación de precisión. No hubo despliegue o push en esta tarea. La selección real de las nuevas duraciones queda pendiente del chequeo dirigido preparado; no se atribuye a este arreglo una mejora de asociación o de revisión.
