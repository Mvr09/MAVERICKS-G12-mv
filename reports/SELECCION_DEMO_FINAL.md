# Selección cerrada de la demo · 19-10-2026

## Decisión operativa

**Usar `radar-1.0.0-candidate` (preguntas3.4.2 / revisión1.3.1) de forma explícita en la demo. Mantener 1.0.0 como predeterminado.** Matching3.3, riesgo1.2, duración1.1, transporte1.0 y JEV1.13.0 quedan congelados en `demo-selection-freeze.json`. No hay promoción global ni cambios de preguntas, umbrales o fórmula en esta entrega.

La candidata recupera omisiones relevantes y automatiza más decisiones correctas, pero conserva asociaciones demasiado amplias y falsas urgencias revisadas. El criterio congelado exigía mantener el default; los controles propios y training no acreditan generalización independiente en noticias reales. La selección es reversible: elegir1.0.0 en la siguiente ejecución, conservando versiones e historial.

## Comparación pareada almacenada

Mismas entradas por perfil, incluidas **todas las revisadas**. Training30 y controles14 se mantienen separados. Ambos ya inspeccionados: no son una evaluación independiente ni un test nuevo. Cuatro controles adicionales con información insuficiente no entran en los14denominadores; los cuatro siguen revisados en la candidata. En controles, el baseline conservó su semántica con fanout; no es un ensayo de latencia del default original.

| Muestra | Perfil | Decisión | TP/FP/FN | Precisión | Recall | F1 |
|---|---|---|---|---|---|---|
|Training30|1.0.0|Riesgo|10/0/4|1.000|0.714|0.833|
|Training30|1.0.0|Urgencia|5/3/0|0.625|1.000|0.769|
|Training30|1.0.0|Proveedores|13/1/9|0.929|0.591|0.722|
|Training30|3.4.2|Riesgo|13/0/1|1.000|0.929|0.963|
|Training30|3.4.2|Urgencia|5/2/0|0.714|1.000|0.833|
|Training30|3.4.2|Proveedores|22/3/0|0.880|1.000|0.936|
|Controles14|1.0.0|Riesgo|4/0/4|1.000|0.500|0.667|
|Controles14|1.0.0|Urgencia|2/0/0|1.000|1.000|1.000|
|Controles14|1.0.0|Proveedores|9/0/1|1.000|0.900|0.947|
|Controles14|3.4.2|Riesgo|8/0/0|1.000|1.000|1.000|
|Controles14|3.4.2|Urgencia|2/0/0|1.000|1.000|1.000|
|Controles14|3.4.2|Proveedores|10/1/0|0.909|1.000|0.952|

| Muestra | Perfil | Proveedores exactos | Revisadas | Automáticas/cobertura | Errores entre automáticas |
|---|---|---|---|---|---|
|Training30|1.0.0|25/30|16/30|14/30 · 46.7%|2/14|
|Training30|3.4.2|29/30|14/30|16/30 · 53.3%|0/16|
|Controles14|1.0.0|13/14|11/14|3/14 · 21.4%|0/3|
|Controles14|3.4.2|13/14|8/14|6/14 · 42.9%|0/6|

### Positivos y negativos automatizados

TP/TN/FP/FN aquí se refieren exclusivamente a los casos automáticos. La columna de proveedores cuenta noticias con/sin proveedores de referencia; TP/FP/FN de asociaciones se conservan en el JSON. No confundir ausencia de urgencia con ausencia de riesgo.

| Muestra/perfil | Riesgo TP/TN/FP/FN | Urgencia TP/TN/FP/FN | Con/sin proveedor de referencia | Conjunto exacto automático |
|---|---|---|---|---|
|Training30/1.0.0|2/10/0/2|2/12/0/0|7/7|12/14|
|Training30/3.4.2|3/13/0/0|3/13/0/0|5/11|16/16|
|Controles14/1.0.0|1/2/0/0|0/3/0/0|1/2|3/3|
|Controles14/3.4.2|2/4/0/0|1/5/0/0|2/4|6/6|

La automatización correcta de riesgo positivo pasa2→3 en training y1→2 en controles; la urgencia positiva correcta pasa2→3 y0→1. Esto aporta más que liberar negativos inocuos. El baseline conserva dos errores automáticos de training; la candidata ninguno en estas muestras, lo que no garantiza cero errores futuros.

## Errores concretos y consecuencia para compras

- **N025, salida inmediata del CEO de PolarChain:** una omisión de riesgo con sucesión interina anunciada, pero sin interrupción publicada de entregas. S030 es crítico alto, no fuente única, servicio sin inventario físico ni productos mapeados. La candidata conserva identidad y revisión; corresponde confirmar continuidad operativa y gobernanza, sin inventar paradas. No esconder esta omisión tras el F1.
- **N037, bajada del Rin:** asociaciones adicionalesS004 (API/atorvastatina→Lipivia),S015 (viales→HX-mAb) yS038 (solventes/productos no mapeados). S004/S015 son críticos altos,S038medio; ninguno fuente única. Ubicación y actividad no prueban uso de barcazas ni entregas afectadas. Se mantienen revisadas: confirmar ruta/modalidad y alcance antes de cambiar suministro. Una asociación falsa puede desviar atención incluso sin riesgoFPpor noticia.
- **N053, huelga en Rotterdam**, y **N057, bloqueo cerca de Hsinchu**: dos urgencias positivas frente a referencia no urgente. S030/S038 yS027 quedan revisados por vínculo/soporte/urgencia; no se valida que tres o dos días impliquen desabastecimiento inmediato. S027 crítico alto,45días inventario/65lead time, sin producto mapeado. Contactar y confirmar entregas/plazo; no lanzar un pedido alternativo por la clasificación dudosa.
- **Control `named_road_slowdown`:**S030 está nombrado, pero se añadeS031 sin acreditar su participación. La FPde proveedor se mantiene revisada; no aumenta el FPde riesgo por noticia porque existe un proveedor realmente expuesto. Verificar operador/servicio antes de atribuir daño.

## A06: datos suficientes frente a datos ausentes

**S024:** Hangzhou→Zhejiang tiene procedencia verificable. El default había omitido su exposición. La comprobación única de N044 con3.4.2 congelada recuperaS024 (vínculo0,85,riesgo0,69,urgencia0,22), pero sigue revisado por soporte de riesgo y estado del impacto. Se presenta como exposición potencial, no entrega individual confirmada. El componente de matching mejora; no queda automáticamente aprobado todo el caso.

**S003:** Taizhou continúa sin provincia confirmada. N044 produce vínculo0,63/riesgo0,76/urgencia0,56 y revisión por geografía, vínculo, soporte y urgencia. La salida incluyeS003, pero no es una asociación validada; la urgencia agregadaY procede de este candidato dudoso, mientrasS024esNo urgente. No afirmar Jiangsu/Zhejiang ni recuperar una ubicación de la etiqueta esperada. Hace falta dirección/provincia verificable de ese proveedor. La mención explícita deS003 enN001del recorrido de demo sí permite identidad directa; no resuelve su geografía regional.

N044 solo se usó como comparación retrospectiva congelada: cuatro peticiones, sin modificar preguntas ni usarlo como nueva validación. **A06 permanece falla/abierto.** La capacidad de multiselección, la recuperación deS024 y la limitación deS003 se registran por separado.

## Dos HTTP400: desenlace persistido

1. **Local, `unknown_transport_mode`, prior3.0:** B rechazado con25candidatos/325preguntas/352446bytes. El proveedor no comunicó causa exacta; no afirmar un límite documentado. La llamada estaba conservada, pero el runner dejó la noticia pendiente sin análisis. Se corrigió a **error explícito, riesgo/urgencia null**, idempotente y sin borrar el intento. El reemplazo compacto3.4.2 termina revisado; el original3.0 sigue fallido. No se repite el cuerpo rechazado ni se sustituye porN.
2. **Railway, noticia Asia–Europa de The Loadstar:** BHTTP400 original, job ygeneración fallidos conservados. Se diagnosticó antes de ejecutar una nueva generación, corrigiendo extracción de un solo artículo y fanout. Generación3, preguntas3.3/revisión1.2, terminó con éxito técnico en revisión,N/N,sin proveedor. EseN/N procede de nuevas respuestas válidas, no del fallo. No se afirma que esa noticia se haya recuperado con3.4.2; el RSS3.4.2 válido deNamibia se conserva aparte.

La primera tentativa de ese RSS tuvo dos peticiones: A200 yB400. **Solo una falló**. El otroHTTP400 fue el experimento local. Auditoría exacta en `demo-failure-outcomes.json`; contador y error originales preservados.

## Recorrido congelado y consumo de este cierre

- Excel privado `Demo_training_3_filas.xlsx`: subconjunto realN001/N002/N005, seis columnas de inferencia, sin etiquetas; no cambia originales. Importado enRailway, elegida candidata, tres terminadas con sus versiones, exportación200 de3filas y orden preservado. **Cuatro peticiones nuevas200, cero reintentos, cero etapas cacheadas**. No mezclar este ensayo de integración con otra evaluación independiente de training.
- N001→S003nombrado→M02Metformin hydrochloride→Glucora850mg→siguiente acción→borrador editable guardado. Revisión real a390/1440, sin overflow ni erroresJS. Noticias y proveedores conservan evidencia y exposición; no se confirmó stock alternativo.
- RSS individual: reutilizado análisis válido3.4.2 deNamibia, categoríaIncendio forestal,N/N,sin vínculo,solo resumen identificado; historial yversiones comprobados enambos anchos. **Cero nuevas peticionesRSS**; el smoke previo de2llamadas se conserva como evidencia de procesamiento, no se repite.
- Estados de error:126unit/integración con mocks ypruebas UI dirigidas; error real422deExcel inválido sin crear lote ni gastarJEV. No se provoca un fallo pagado para animar la demo.

Este cierre: **8peticiones nuevas200 (4retrospectiva+4integraciónExcel), cero reintentos**; comparación88predicciones almacenadas sin llamadas. Contador local1036→1040;Railway ejercicio91→95,RSS62→62. Uso reportado en informes, sin inventar coste monetario. El análisis periódico RSSde pago sigue desactivado.

**A14 cerrado** por prueba física heredada del usuario, ordenador/Firefox, unaQA automática audible. **A20 histórico** b4d697b,14LiveDay,7,888295967s,23nuevas/0caché/0reintentos. No hay nueva versión semántica, promoción ni ejecuciónLiveDay; no se renueva A20 yno se atribuye ese tiempo a3.4.2. Este cierre no certifica300s para la candidata.

## Guion definitivo

Usar `docs/09_DEMO_PROCUREMENT.md`: la historia principal ahora es el training de3filas procesado con3.4.2; fuentes yRSS individual sirven de contraste real sin vínculo, no se mezclan perfiles antiguos ni se simula riesgo en una noticia irrelevante. Configuración y rollback están congelados; test yLiveDay no se reabrieron para desarrollo.
