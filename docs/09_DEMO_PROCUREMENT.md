# Guion definitivo · cuatro minutos

[Demo pública](https://mavericks-g12-mv-production.up.railway.app).

## Configuración congelada

Usar **Candidata · exposición y revisión focalizada**: preguntas **3.4.2**, matching **3.3**, revisión **1.3.1**, riesgo **1.2**, duración **1.1**, transporte **1.0**, modelo **jev-1.13.0**. **1.0.0 continúa predeterminada**; seleccionar la candidata explícitamente al ejecutar Excel o una noticia RSS. No mezclar resultados antiguos como si usaran ese perfil.

Entrar como presentador. En **Resumen → Ejercicio → Origen de los datos**, elegir `Demo_training_3_filas.xlsx`. Es un subconjunto de tres entradas reales de training, preparado sin etiquetas, procesado y exportado en Railway. No es una evaluación nueva. Los originales están intactos; el Excel privado no se publica como asset. El lote ya terminado no necesita volver a analizarse para ensayar.

Historia principal: **Fire at Taizhou chemical park forces evacuation of several API plants**, N001 → **Taizhou Hengyuan Pharma (S003)** → **Metformin hydrochloride (M02)** → **Glucora 850 mg tablets**. El proveedor está nombrado explícitamente: esto permite identificarlo sin inventar su provincia. La noticia no confirma nuestras entregas particulares.

RSS de contraste: **Green forest fire notification in Namibia**, GDACS, preguntas3.4.2/revisión1.3.1, analizado sin vínculo con la cartera. Solo resumen RSS disponible, identificado como tal. Reutilizar el resultado válido; no llamar JEV de nuevo para animar el recorrido. El RSS periódico de pago permanece desactivado.

## Recorrido

| Tiempo | Acción y mensaje |
|---|---|
| 0:00–0:35 | **Resumen / Ejercicio / lote de tres filas.** Mostrar el archivo y las versiones. «Esta es una cartera ficticia de Helixa. El radar ordena atención de compras; no estima probabilidad de quiebra». Para explicar la ingesta, mostrar progreso y resultado ya guardados. Si se carga otro archivo de training autorizado, elegir la candidata antes de Analizar. No reejecutar por espectáculo. |
| 0:35–1:15 | **Noticia N001 → evidencia.** Leer el fragmento que nombra al proveedor y su línea de metformina. «El análisis es automático y la atención de compras inmediata: son conceptos diferentes». La duración es un límite inferior de tres semanas, no una fecha de recuperación garantizada. |
| 1:15–2:05 | **S003 → Impacto y siguiente acción → material M02.** Mostrar prioridad y sus factores, criticidad, fuente única, inventario y lead time. Abrir el producto Glucora. «El mapeo indica posible exposición del producto; no demuestra una entrega incumplida ni una rotura de stock». Comparar inventario y lead time sin inventar consumo o capacidad. |
| 2:05–2:45 | **Consultar proveedor → borrador editable.** Mostrar el borrador guardado del ensayo. Pedir confirmación de entregas comprometidas, continuidad y plazo estimado. Editar, guardar, copiar o descargar TXT. «No se envía nada». Si se consulta al alternativo, confirmar primero adecuación, disponibilidad y plazo: el catálogo no confirma stock. |
| 2:45–3:25 | **Noticias reales / GDACS / Namibia.** Mostrar categoría Incendio forestal, resumen y versiones del historial. «Una noticia grave puede ser irrelevante para esta cartera: no fabricamos un proveedor afectado». En Fuentes, mostrar las seis últimas consultas; Actualizar ahora consulta RSS y muestra progreso sin activar análisis periódico pagado. Un304 significa consulta sin cambios. |
| 3:25–4:00 | **Alerta y exportación.** Mostrar una acción ligada a su incidente. Para audio reproducible, identificar «Prueba de aviso automático · presentador», Activar sonido → programar QA5s → esperar5–8s con pestaña abierta; respetar30s de cooldown. QA está fuera de métricas JEV. Volver a Resumen y exportar el lote de tres filas. No es una medición A20. |

## Incertidumbre y contingencias

- **Requiere revisión** indica una conclusión que puede cambiar proveedor, riesgo, urgencia o acción. **Atención inmediata** indica prioridad de compras y puede coexistir con análisis automático. Las observaciones auxiliares no se esconden ni bloquean todo indiscriminadamente.
- La provincia de S003 sigue desconocida. Una noticia regional que no lo nombre exige verificar alcance; la identificación directa de N001 no resuelve ese dato del catálogo.
- Una fuente caída deja estado y última consulta visibles; las demás continúan. Una noticia pendiente nunca significa sin riesgo. Un error conserva el intento y bloquea la exportación del lote hasta resolverlo.
- Un Excel corrupto muestra «El archivo XLSX está corrupto», no crea un lote y permite elegir otro archivo. No provocar errores pagados durante la presentación.
- Los filtros y el foco se conservan al volver a Noticias; los contextos Ejercicio y Noticias reales permanecen separados. La consulta guardada se recupera de PostgreSQL.

## Evidencia y límites

El recorrido de la candidata se comprobó en web real a **390 y1440px**, con exportación200 de tres filas en orden, evidencia, proveedor, material/producto y borrador editado/persistido. Coste de ejecución: cuatro peticiones JEV200, cero reintentos y cero etapas cacheadas. Se reutilizó el RSS válido sin consumo. Son comprobaciones funcionales, no una nueva evaluación estadística ni un estudio de comprensión con compradores. Los anchos360/768 y la lógica de errores/foco también conservan pruebas identificadas con mocks.

**A06 abierto. A14 cerrado** por la prueba física comunicada en ordenador/Firefox: una QA automática audible, sin Probar alarma. No se promete sonido con navegador suspendido o pestaña cerrada. **A20 histórico**, b4d697b,14LiveDay,7,888295967s,23nuevas/0caché/0reintentos; no se repite ni se atribuye al candidato.

Selección, errores y métricas completas: [SELECCION_DEMO_FINAL.md](../reports/SELECCION_DEMO_FINAL.md). Configuración congelada: [demo-selection-freeze.json](../reports/demo-selection-freeze.json). Para volver al baseline, elegir **1.0.0** en una ejecución nueva, conservando el historial.

## Comandos del ensayo dirigido

```bash
# Solo prepara training; conserva el subconjunto existente y nunca abre retenidos.
.venv/bin/python -m scripts.prepare_demo_training
# Requiere credenciales locales y acceso autorizado al proyecto.
# Reutiliza el lote terminado; no lo reanaliza silenciosamente.
node scripts/check_demo_selected_runtime.mjs
# Comparación desde resultados privados ya almacenados, sin llamadas.
.venv/bin/python -m scripts.close_demo_selection
```

Los informes privados del desarrollo no se publican; la comparación agregada queda en demo-selection-comparison.json. El ensayo navega el servicio público configurado y puede crear un borrador; no envía comunicaciones. No ejecutar comandos de test/LiveDay para este recorrido.
