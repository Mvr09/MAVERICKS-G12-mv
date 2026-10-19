# Demo de compras · cuatro minutos

URL: https://mavericks-g12-mv-production.up.railway.app

## Preparación

Entrar como presentador. **1.0.0 sigue predeterminada.** «Candidata · exposición y revisión focalizada» selecciona 3.4.2/revisión 1.3.1, con matching3.3 en Excel y RSS individual; conserva versiones e historial. 2.2 permanece como experimental anterior. El análisis RSS periódico de pago está desactivado.

Abrir **Asia-Europe spot rates on the rise ahead of new FAK hikes**, de The Loadstar. Su análisis requiere revisar el vínculo: no confirma riesgo, urgencia ni proveedores vinculados por la decisión. Existe una consulta guardada a Oceanbridge con una hipótesis humana explícita. No reanalizar una respuesta válida solo para animar la presentación.

Para mostrar materiales y productos, abrir otra pestaña en Resumen/Ejercicio y seleccionar un archivo en «Origen de los datos». El training no está importado en el Railway observado. Se pueden mostrar resultados normalizados existentes de validación, identificados como retrospectivos, sin abrir referencias ni utilizarlos para ajustar JEV. La exportación de 14 filas ya completada se descarga sin ejecutar LiveDay otra vez.

## Guion

| Tiempo | Recorrido y mensaje |
|---|---|
| 0:00–0:30 | **Fuentes / Noticias reales.** «Monitorizamos seis fuentes para una cartera ficticia de Helixa». Mostrar última consulta, estado y worker. «Actualizar ahora» consulta RSS reales y muestra progreso. Un 304 indica consulta sin cambios; si no hay novedades, decirlo. |
| 0:30–1:15 | **Noticias → The Loadstar → buscar Asia-Europe → abrir noticia.** Mostrar categoría, fecha y lectura editorial. «Esta es una señal comercial; el sistema no confirma un proveedor afectado. Estas son las dudas sobre el alcance». Abrir las hipótesis si se necesita detalle. Volver conserva filtros, foco y contexto. |
| 1:15–1:55 | **Consulta de verificación / Oceanbridge.** Mostrar servicio marítimo Asia–Europa, criticidad, fuente única, inventario no aplicable y lead time. «No conocemos embarques afectados; Productos no mapeados es un dato ausente». El alternativo ofrece ferrocarril: primero confirmar adecuación; después disponibilidad y plazo. |
| 1:55–2:40 | **Cita → hipótesis → borrador.** Abrir «Consultas guardadas», editar y guardar una pregunta sobre tarifas o capacidad aplicables. Copiar o descargar TXT. «Esto pregunta por una exposición posible; no cambia JEV, score ni alertas y no envía nada». Recargar y recuperar la consulta para mostrar persistencia en PostgreSQL. |
| 2:40–3:25 | **Ejercicio → Resumen con archivo seleccionado → proveedor → material.** Mostrar una incidencia existente con evidencia, prioridad y siguiente acción. Abrir especificaciones y productos mapeados. Explicar criticidad, fuente única, inventario y lead time. Consultar entregas y continuidad; no atribuir stock al alternativo. |
| 3:25–4:00 | **Alerta y salida.** Mostrar la acción de su incidente. Para sonido reproducible: «Prueba de aviso automático · presentador» → Activar sonido → programar QA 5 s; esperar 5–8 s con pestaña abierta. Identificarlo como prueba, separada de JEV; respetar 30 s de cooldown si hubo sonido previo. En Resumen, exportar el lote de 14 filas ya completado. La descarga no es una nueva medición A20. |

## Mensajes verificables

- Una noticia grave respaldada puede analizarse automáticamente y pedir acción inmediata. Revisión significa una duda relevante; no significa urgencia por sí sola.
- La compatibilidad regional y material representa exposición potencial. La atribución publicada a un proveedor no constituye corroboración externa ni confirma nuestras entregas.
- Las hipótesis pendientes y las exclusiones sustentadas se muestran por separado. Una exclusión dudosa todavía puede ocultar una omisión; permanece accesible y revisada.
- La prioridad ordena atención empresarial. Conserva la fórmula y los datos desconocidos; no representa una probabilidad de quiebra ni una fecha garantizada de rotura de stock.
- No se prometen ahorros, pérdidas evitadas o disponibilidad no medidos. Consultar al alternativo no crea un pedido.

## Evidencia y límites

`reports/window-rss-evidence.json` conserva el sondeo y dos análisis RSS reales, el HTTP 400 diagnosticado y la recuperación: 11 peticiones, cero reintentos y contador RSS 49→60. El incendio tardó 4,42 s desde clic hasta resultado visible. El tiempo exacto de fletes no quedó registrado; se conserva como desconocido.

`reports/window-demo-evidence.json` registra los guiones de lectura: 1440 px, 240,026 s; 390 px, 240,038 s. También edición, guardado, copia, TXT y cuatro anchos. Son pausas de lectura, no latencia JEV. La última etapa visitó Fuentes; la descarga se completa después desde Resumen en `window-final-ui.json`, junto a las capturas finales. Es emulación de viewport y revisión heurística, no un estudio de comprensión con compradores.

**A14 físico**: el usuario acreditó una única alerta automática QA en ordenador/Firefox sin pulsar Probar alarma. No se promete sonido con pestaña cerrada, navegador suspendido o teléfono bloqueado. Los umbrales por proveedor e incidente se conservan: una urgencia visual puede no ser audible.

**A20 histórico**: b4d697b, 18-10-2026, 1.0/jev1.13/duration1.1, 14 LiveDay, 7,888295967 s hasta exportación, 23 peticiones nuevas y cero caché/reintentos. No se traslada al candidato, RSS o los cuatro minutos de lectura.

**A06 sigue abierto.** La candidata conserva el matching3.3 que recupera asociaciones relevantes en desarrollo, pero conserva falsos vínculos, falsas urgencias y omisiones revisadas. S003 mantiene provincia desconocida. La candidata queda seleccionable; no sustituye al default.

## Contingencias

Una fuente caída muestra su error y permite continuar con las otras. Un análisis fallido conserva el error y requiere diagnóstico antes de reintentar; nunca se convierte en N. Una noticia irrelevante es un resultado válido. Si faltan datos, preparar una pregunta con hipótesis explícita; no fabricar relaciones ni cambiar umbrales para la demo.

Si falla el gráfico, Analítica mantiene los recuentos y ofrece recargar la vista. Los filtros de Noticias se conservan durante la sesión y se mantienen separados por contexto. No limpiar datos o consumo para ensayar ni activar RSS periódico de pago.


### Comprobación de la candidata actual

`reports/rss-smoke-342.json`:una noticia GDACS pendiente, **Green forest fire notification in Namibia**, procesada enRailway con preguntas3.4.2/revisión1.3.1 yJEV1.13. Dos peticiones nuevas, cero reintentos; contadorRSS60→62. Resultado automático sin riesgo/urgencia ni vínculo con esta cartera, categoríaIncendio forestal. Solo se pudo usar el resumenRSS; HTTP200 de la página no permitió extraer texto editorial. No se presenta como precisión medida.

Se observaron8,428s desde clic hasta el aviso de trabajo completado, con cola ysondeo incluidos. No se midió el primer pintado del resultado ni se afirmó una comprobación real de historial sin recargar para este smoke; esa conducta está cubierta por pruebas de interfaz yel recorrido real anterior3.3. Los resultados ylas versiones persistidos se comprueban después sin consumirJEV.

Capturas: [noticia móvil](../reports/window-final-article-390.png), [consulta móvil](../reports/window-final-draft-390.png), [productos](../reports/window-final-products-390.png), [proveedor escritorio](../reports/window-final-supplier-1440.png). Son datos de la demo publicada, sin fixtures visuales.
