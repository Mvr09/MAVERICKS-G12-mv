# Aceptación actual · Supplier Risk Radar

Registro:19-10-2026. **19 pasa /1 falla (A06).** Default **1.0.0**; única candidata seleccionable **3.4.2/revisión1.3.1**, sin promoción. Versión funcional y HTTP observados en `window-final-verification.json`; esta matriz distingue herencia de ejecución nueva.

| ID | Estado | Evidencia y límite |
|---|---|---|
|A01|pasa|Catálogo público actual:40 proveedores y fichas accesibles.20 materiales y6 productos heredados del catálogo sin cambios;40 Noul y proveedores sin Materials cubiertos por integración. No se reabrieron originales.|
|A02|pasa|Importador y cuatro esquemas heredados sin cambios. La prueba UI sintética conserva carga→origen→progreso→exportación y usa un buffer MOCK, no LiveDay real. No se repiten importaciones retenidas.|
|A03|pasa|Unit/integración inspecciona el payload efectivo con cinco centinelas de etiquetas excluidos. El candidato, soporte, RSS y transporte mantienen whitelists; las particiones conservan el mismo estado sin añadir etiquetas.|
|A04|pasa|Controles de homónimos y geografía inocua heredados y nueva muestra controlada pre-referenciada. Los cinco negativos de training liberados por revisión1.2 conservan exclusión factual; rutas desconocidas no se convierten en exclusiones ciertas.|
|A05|pasa|Dos controles positivos nuevos conservan identidad y N/N automáticamente; integración verifica este contrato en la candidata. No se impone riesgo por identificar un proveedor.|
|A06|falla|Abierto:default omiteS024 con geografía respaldada. Diagnóstico3.4.2 congelado deN044 recuperaS024 como exposición potencial,riskY/urgentN,pero mantiene revisión por soporte/impacto. S003 provincia desconocida;el modelo lo incluye con vínculo0,63 yurgencia0,56,revisados,no asociación validada. La mejoraS024 no resuelveS003 ni la urgencia agregada dudosa. Sin ajustes conN044.|
|A07|pasa|Reconciliación afectada por reanálisis comprobada en PG aislado: no suma titulares, retira solo efectos de la generación sustituida y mantiene máximo de incidentes activos. No se llama recuperación a una clasificación sustituida.|
|A08|pasa|Pruebas dirigidas conservan recuperación compatible, historia y cierre manual autoritativo; una noticia antigua tardía no reabre por sí sola. Reanálisis compartido no cierra otro incidente. No se fuerzan cierres en producción para probar.|
|A09|pasa|Inventario físico desconocido, cero y servicio no aplicable conservados. Las advertencias de prioridad quedan localizadas en candidata; no se inventan stock, lead time o capacidad. La falta de datos relevantes para la decisión sigue revisada.|
|A10|pasa|Fórmula1.0, umbrales y scoring de referencia intactos. Pruebas mantienen score0–100, fuente única una sola vez y confianza separada. Duración1.1 heredada; ningún ensayo no adoptado cambia el motor operativo.|
|A11|pasa|Seis consultas reales terminadas por el worker a2e962f:2HTTP200/4HTTP304; JEV60→60. Fuente y hora en window-final-rss-sync.json;304 no es contenido nuevo. Dos análisis manuales3.3 previos y un nuevo3.4.2 de Namibia:incendio forestal,N/N,sin vínculo,solo resumen identificado,2HTTP200. TotalRSS13peticiones nuevas,12HTTP200/1HTTP400 diagnosticado; contador49→62; pago periódico false.|
|A12|pasa|RSS/Atom,304, GUID actualizado, versiones, duplicados y XML peligroso heredados sin cambios. Parser editorial corregido y probado:elige el artículo propio, no ticker/vecinas. Reanálisis guarda snapshots de versiones anteriores y fecha real de lectura.|
|A13|pasa|Errores no son negativos. DosHTTP400 de la ventana registrados y diagnosticados antes de insistir. Fanout conserva estado/preguntas completos y caché. Guardas persistentes de36intentos por generación y deadline; run_key de generación0 vacío sigue acotado por artículo. Mocks401/429/reintentos y contratos pasan.454peticiones nuevas:452HTTP200/2HTTP400,0reintentos; contadores preservados. Cierre:ambosHTTP400auditados. El caso localpendiente se corrigió aerror explícito/riesgo-urgencianull,sin sobrescribir respuestas válidas ni gastarJEV;126tests pasan. Railway conserva job ygeneraciónerror,recuperación3.3 revisada separada.|
|A14|pasa|Cerrado. Evidencia física del usuario:ordenador/Firefox,Activar sonido→programar alertaQA5s→una única alerta automática audible sin Probar alarma. Activar/probar/silenciar/probar también confirmado. Audio y umbrales intactos; pruebas de elegibilidad por proveedor/incidente, historial, foco,cooldown,mute yQA heredadas/mocks. No se atribuye audibilidad a Playwright ni se afirma prueba física móvil; OS/versión deFirefox no informados.|
|A15|pasa|ConsultaRSS real con cita e hipótesis:edición,guardado,copia con readback,TXT y recarga a4anchos. Borrador creado en4a818c1 persiste tras autodeploya2e962f. Oferta ferroviaria propia del alternativo visible; se pregunta adecuación antes de disponibilidad/capacidad. Continuidad de edición probada, sin envío externo.|
|A16|pasa|Dos descargas reales390/1440 desdeResumen,HTTP200,ZIPXLSX válido y14filas contadas por estructura sin leer valores de celdas. Solo exportaciónLiveDay ya completada,0reanálisis; no se usa para ajustar. Contrato de IDs/orden/delimitador y bloqueo de errores heredado del exportador sin cambios. Candidata3.4.2:exportación real200 de3training,sin etiquetas de entrada,News_ID/orden ycolumnas verificados;noA20.|
|A17|pasa|Esquema0008 y migración aditiva heredados; web/worker compatibles observados en HTTPS. Draft y análisis anteriores sobreviven a autodeploy. Pruebas PG aisladas de generaciones y rollback de proyección al fallar. No se simula una caída destructiva del worker en Railway.|
|A18|pasa|a2e962f:web yworker compatibles,HTTPS,/,healthz/readyz,5assets,catálogo40,ficha/rutas profundas200;administración y análisis401 anónimos yoriginales404. Modelo protegido renderiza candidata3.4.2/revisión1.3.1,441llamadas locales yensayos descartados sin erroresJS. Paquete112archivos sin .env,originales ni referencias protegidas; sesiones/permisos probados.|
|A19|pasa|HTTPSa2e962f en360/390/768/1440:sin overflow/erroresJS;filtros,foco,contexto,Escape yconsulta persistida. Material yproductos esperados cargados,oferta propia del alternativo visible.26E2E distintos con mocks. Guiones4min1440/390 más repetición de pasos afectados; emulación,no estudio de compradores ni móvil físico. JS inicial215653→118897bytes codificados observados,44.87%menos; no es latencia niA20. Nuevo recorrido3.4.2 real390/1440,Excel→noticia→proveedor→M02/Glucora→borrador;8E2E mock dirigidos yerror real422sin lote ni consumo.|
|A20|pasa|Pasa histórico, no medición actual ni del candidato:b4d697b,18-10-2026,1.0.0/jev1.13/duration1.1,14LiveDay,7.888295967s hasta exportación,23 peticiones nuevas/0caché/0reintentos. Se conservan datos/fecha/perfil; no se repite LiveDay para desarrollo. Preguntas/normalizador/fórmula/duración/exportación default permanecen; la nueva orquestación opcional y UI no renuevan por sí solas esa certificación. No extrapolar tiempo al candidato/RSS.|

## Interpretación y vigencia

A06 separa capacidad funcional (40Noul y selección múltiple), errores semánticos conocidos y datos de catálogo ausentes. No exige precisión perfecta; la omisión regional respaldada todavía impide cerrarlo. S003 permanece sin provincia confirmada. Las métricas incluyen todas las predicciones revisadas; reducir revisión no demuestra por sí solo mejor clasificación.

Los24 sintéticos de la comparación original3.3 se redactaron antes de sus llamadas y se congelaron. Ya inspeccionados, se usaron después solo como desarrollo para dos intentos descartados. La3.4.2 usó después esos24 como desarrollo. Una nueva muestra de18controles fue referenciada y congelada antes de consultar;14tienen referencia completa y4siguen indeterminados/revisados. No es prueba independiente de precisiónRSS. Validation sigue retrospectiva; no hubo test,LiveDay ni answer key para ajustar.

A14 está cerrado por evidencia física comunicada por el usuario en ordenador/Firefox y la lógica comprobada. Probar alarma y aviso automáticoQA son pruebas distintas; el segundo se escuchó una sola vez sin pulsar Probar. La rutaQA queda fuera de métricasJEV.

A20 conserva una medición histórica:fecha,commit,perfil,14filas,tiempo y23llamadas nuevas explícitos. El default semántico no cambió; hubo cambios de orquestación para perfiles opcionales y presentación. Esta herencia no certifica una ejecución actual ni el tiempo del candidato. Los guiones4min,los mocks y el incendio4,42s no sustituyen la medida14filas.

## Evidencias vigentes

- `candidate-342-results.json`, `window-fresh-342-freeze.json`, `window-fresh-342-controls.json`: comparación final congelada, referencias propias y límites.
- `rss-smoke-342.json`:análisis real3.4.2 y uso reportado;8,428s hasta estado de trabajo completado observado, no primer pintado.
- `window-candidate-results.json`, `CANDIDATA_OPERATIVA.md`:métricas de todas las predicciones, cobertura,errores automáticos,causas,consumo y decisión.
- `window-risk-results.json`, `window-risk-current-results.json`, `risk-contract-replay.json`:intentos descartados y reproducción sin red.
- `window-rss-evidence.json`:consultas/análisis RSS reales, fallo diagnosticado y recuperación.
- `window-demo-evidence.json`:guiones con pausas,edición/copia/TXT y persistencia; la descarga se completa desdeResumen yse comprueban14filas estructurales,sin reanálisis.
- `window-final-ui.json`, `window-final-verification.json`:últimas observaciones reales y límites.
- `window-assets-before.json` y comparación final:carga deJS observada, sin extrapolar rendimiento.

Referencias/filas protegidas y payloads privados permanecen fuera de Git,Docker y APIpública. Historial anterior conservado enGit y AUDITORIA.md.


## Cierre observado

Código funcional **a2e962f**, web yworker del mismo commit, esquema0008.124pruebas unitarias/integraciónPG y26E2E distintos dirigidos pasan; build ypaquete112archivos revisados. Las seis fuentes se consultaron desde ese worker yse conservaron sus estados reales. La comprobación final no consumió JEV (60→60). Los dos Excel descargados contienen14filas estructurales; no se reevalúa LiveDay.

Se conservan los límites de cada evidencia:un HTTP200 de rutaHTML no demuestra por sí solo que la UI haya cargado; por eso se esperaron datos yse revisaron capturas. Una captura inicial de material mostrabaCargando yse sustituyó tras comprobar el encabezado ylos datos. Un foco perdido al saltar ahipótesis se corrigió yse verificó en web real. Los resultados del modelo no se modificaron durante estas comprobaciones.

## Selección de demo cerrada · 19-10-2026

Usar3.4.2/revisión1.3.1 explícitamente;default1.0.0 conservado. Comparación pareada30training y14controles ya inspeccionados en [SELECCION_DEMO_FINAL.md](SELECCION_DEMO_FINAL.md).126unit/integración y8E2E dirigidos pasan;recorrido real Excel/exportación/proveedor/material/borrador yRSS válido en390/1440. Ocho nuevas peticiones200,cero reintentos. A06permanece abierto,A14cerrado,A20histórico sin renovar.

## Ampliación operativa · revisión y seguimiento

Esquema0009aditivo,24tablas verificadas enbase aislada;141unit/integración y26E2E dirigidos con mocks pasan. Decisiones humanas,notas yacciones separadas deAnalysis,etiquetas yexportación delreto. Recuperación preliminar medida solo entraining:19→20TPde22referencias,5candidatos adicionales iguales;7controles dedesarrollo pasan,sin nueva precisiónJEV. Publicación ypersistencia externas se registrarán enoperational-public.json. A06abierto;A14yA20conservan evidencia yalcance.
