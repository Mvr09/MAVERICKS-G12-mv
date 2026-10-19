# Candidata seleccionable · 3.4.2 / revisión 1.3.1

**Default 1.0.0 se conserva.** La única candidata seleccionable es `radar-1.0.0-candidate`: matching `link-3.3.0`, preguntas `decision-3.4.2`, revisión `review-1.3.1`, riesgo `risk-focus-1.2.0`, transporte `fanout-1.0.0` y modelo `jev-1.13.0`. Disponible para Excel y RSS individual, con versiones fijadas por trabajo e historial conservado. No se promociona al default.

## Corrección y decisión

El ensayo anterior solo refinaba probabilidades de riesgo en la banda gris; omitía negativos fuera de ella aunque faltase soporte de decisión. Además, su pregunta sobre amenaza «actual» no fijaba la fecha y excluía reducciones futuras definidas. Se amplía la comprobación al negativo sin evidencia suficiente, **solo con asociación previamente sustentada**, y se ancla el hecho a la publicación. Una reducción parcial anunciada sigue siendo riesgo aunque sea pequeña, planificada y con entregas cubiertas.

Se utiliza la probabilidad real del refinamiento con los umbrales originales. Una probabilidad gris permanece revisada. El soporte de un hecho adverso nunca se interpreta como soporte de «sin riesgo»; una contradicción queda en revisión. Una cita seleccionada no prueba asociación. Ubicación, ruta o modo esenciales desconocidos siguen bloqueando su confirmación.

La duda entre impacto activo y seguimiento se localiza únicamente cuando hay soporte de amenaza, asociación y seguimiento no urgente. Se conserva como observación. No cambia la probabilidad de urgencia ni sus umbrales; no habilita sonido ante una urgencia dudosa. Las comprobaciones sobre la misma fuente no constituyen corroboración externa.

## Comparación antes/después

Todas las predicciones revisadas están incluidas. Los conjuntos indeterminados se evalúan aparte; no se convierten en verdaderos negativos.

| Muestra | Versión | Riesgo TP/FP/FN | Urgencia TP/FP/FN | Proveedores TP/FP/FN | Revisadas | Automáticas / errores |
|---|---|---|---|---|---|---|
| Training30 | 1.0 | 10/0/4 | 5/3/0 | 13/1/9 | 16 | 14/30 · 2/14 |
| Training30 histórico | 2.2, duración anterior | 12/0/2 | 5/0/0 | 17/0/5 | 22 | 8/30 · 0/8 |
| Training30 | 3.0 + revisión1.1 | 11/0/3 | 5/1/0 | 21/2/1 | 18 | 12/30 · 0/12 |
| Training30 | 3.0 + revisión1.2, solo política | 11/0/3 | 5/1/0 | 21/2/1 | 13 | 17/30 · 0/17 |
| Training30 | 3.3 | 13/0/1 | 5/2/0 | 22/3/0 | 14 | 16/30 · 0/16 |
| Training30 | 3.4.2 | 13/0/1 | 5/2/0 | 22/3/0 | 14 | 16/30 · 0/16 |
| Controles18 ya inspeccionados, desarrollo | 3.3 | 8/0/2 | 4/0/0 | 13/3/0 | 6 | 12/18 · 0/12 |
| Controles18 ya inspeccionados, desarrollo | 3.4.2 | 10/0/0 | 4/0/0 | 13/3/0 | 2 | 16/18 · 0/16 |
| Controles14 nuevos puntuables | 1.0 | 4/0/4 | 2/0/0 | 9/0/1 | 11 | 3/14 · 0/3 |
| Controles14 nuevos puntuables | 3.3 | 7/0/1 | 2/0/0 | 10/1/0 | 9 | 5/14 · 0/5 |
| Controles14 nuevos puntuables | 3.4.2 | 8/0/0 | 2/0/0 | 10/1/0 | 8 | 6/14 · 0/6 |

La comparación2.2 conserva su extractor de duración anterior: no atribuir todas sus diferencias al matching.

La muestra nueva se redactó a01:09UTC antes de consultar JEV, con referencias razonadas y versiones/criterios congelados. Tiene18 entradas:14 puntuables y4 indeterminadas. Sobre las18, la candidata automatiza6 y revisa12; las cuatro indeterminadas siguen revisadas sin atribuir daños individuales. Sobre las14 puntuables: F1 riesgo1,000, urgencia1,000 y proveedores0,952. Son controles propios, no evidencia independiente de precisión RSS. La comparación utiliza fanout para conservar estado/preguntas dentro del contexto del proveedor; sus tiempos locales incluyen caché y no son rendimiento del default desplegado ni A20.

Se adopta como **opción experimental** porque corrige omisiones de interrupciones limitadas y automatiza más riesgos correctos, manteniendo proveedores y probabilidades de urgencia, sin nuevas falsas urgencias o casos automáticos erróneos. Training no mejora en esta última corrección: conserva una omisión de riesgo, tres asociaciones falsas y dos falsas urgencias, todas revisadas. El nuevo control conserva una asociación falsa heredada y revisada. A06 sigue abierto; S003 no tiene provincia confirmada. La decisión no depende solo de F1 ni de reducir revisión.


### Precisión y cobertura de la muestra nueva

14referencias completas; todas las predicciones, incluidas revisadas. P/R/F1 por decisión.

| Perfil | Riesgo P/R/F1 | Urgencia P/R/F1 | Proveedores P/R/F1 | Conjunto exacto | Cobertura automática |
|---|---|---|---|---|---|
|1.0|1.000/0.500/0.667|1.000/1.000/1.000|1.000/0.900/0.947|13/14|3/14|
|3.3|1.000/0.875/0.933|1.000/1.000/1.000|0.909/1.000/0.952|13/14|5/14|
|3.4.2|1.000/1.000/1.000|1.000/1.000/1.000|0.909/1.000/0.952|13/14|6/14|

La cobertura ylos errores automáticos se puntúan por conjunto de decisiones, no solo por riesgo. Los cuatro casos indeterminados se registran aparte; no tienen etiqueta negativa inventada.

## Consumo y conservación

Esta última hipótesis utilizó14 peticiones de desarrollo y105 en la comparación nueva:119HTTP200, cero reintentos, contador local917→1036. Se reutilizan A/B válidos y preguntas de soporte cuya definición y estado coinciden exactamente. `candidate-342-results.json` registra métricas, causas, uso reportado, caché y latencias; los payloads y las referencias protegidas del reto permanecen privados.

Acumulado de la ventana antes del smoke RSS del nuevo perfil:441 peticiones locales y11 enRailway =452, con dosHTTP400 previamente diagnosticados y cero reintentos. No se borran ni reinician contadores. RSS periódico de pago sigue desactivado. La prueba final de RSS registra cualquier consumo adicional por separado.

Los18 controles nuevos quedan inspeccionados para futuras versiones; su medición original congelada se conserva y no se reutiliza como otra evaluación independiente. No hubo ajuste con validation, test, LiveDay ni answer key.

## Smoke real de la versión seleccionable

A2e962f,web yworker compatibles. Un GDACS pendiente nuevo deNamibia completó análisis con preguntas3.4.2/revisión1.3.1/modelo1.13:dosHTTP200,cero reintentos,contadorRSS60→62. ResultadoN/N,sin proveedor,categoríaIncendio forestal. Se conserva la lectura solo de resumen porque no hubo texto editorial extraíble; no se hace pasar como afectación ni precisiónRSS independiente.

8,428s mide clic→estado de trabajo completado observado,con cola ysondeo; no primer pintado del resultado. No se repitió el resultado válido para comprobar interfaz. El uso reportado por ambas peticiones figura en `rss-smoke-342.json`. **Total final de la ventana:454peticiones nuevas (441locales+13Railway),452HTTP200/2HTTP400diagnosticados,0reintentos.** Contadores595→1036 y49→62 conservados.

La asociación falsa del control nuevo aparece en la noticia sintética de reducción de transporte por carretera deS030:se añadeS031,servicio logístico relacionado no acreditado por la noticia. Está revisada en ambas versiones. No es una nuevaFPderiesgo por noticia porqueS030síestá expuesto; las métricas de proveedores yconjuntos exactos muestran ese error. Antes de mitigar,la acción sigue siendo verificar operador/servicio yentregas; no se supone capacidad del alternativo.

## Reversión

Seleccionar **1.0.0** para una ejecución nueva conserva el historial y desactiva el candidato en ese recorrido. La candidata3.3 anterior está archivada en `scripts/candidate_engine_33.py` y en el commitb995383. Si se necesita restaurarla, hacer un commit hacia delante que recupere motor, versiones, UI y reportes de ese snapshot; comprobar y publicar. No usar force-push, reset destructivo ni borrar resultados. Los trabajos con versión obsoleta requieren diagnóstico y reencolado explícito.

---

## Historial documentado hasta b995383 · candidata anterior 3.3

Las decisiones siguientes son históricas. La selección vigente y la evidencia nueva están arriba.

# Candidata operativa: exposición y revisión focalizada

## Decisión

**1.0.0 sigue predeterminada.** `radar-1.0.0-candidate` selecciona matching/preguntas **link-3.3.0**, revisión **review-1.2.0**, recuperación **3.0**, modelo **jev-1.13.0** y duración **1.1.0**. Disponible de forma explícita para el presentador en Excel, reanálisis y RSS individual. No es una promoción automática ni garantiza precisión en RSS.

Cada ejecución conserva perfil/versiones y resultados anteriores. La cola fija las versiones: un trabajo candidato antiguo no se ejecuta silenciosamente con otra versión después de un despliegue. La reversión funcional consiste en elegir 1.0.0 para una ejecución nueva; los resultados históricos no se reescriben.

## Hipótesis y resultados

Primero se aisló revisión: una pregunta abstracta sobre si la noticia era «no operativa» discrepa con Choice en actividades reales pero ajenas al proveedor. La nueva comprobación pregunta por la **relación concreta actividad–proveedor**, requiere soporte afirmativo de exclusión, fragmento literal y baja identidad/vínculo final. No utiliza ausencia de mención como exclusión. Una ruta o provincia desconocida sigue incierta.

| Training, 30 filas | Riesgo TP/FP/FN | Urgencia TP/FP/FN | Proveedores TP/FP/FN | Revisadas | Automáticas | Errores entre automáticas |
|---|---|---|---|---|---|---|
|1.0.0|10/0/4|5/3/0|13/1/9|16|14/30|2/14|
|3.0 + revisión1.1|11/0/3|5/1/0|21/2/1|18|12/30|0/12|
|3.0 + revisión1.2, predicciones congeladas|11/0/3|5/1/0|21/2/1|13|17/30|0/17|
|3.3 + revisión1.2|13/0/1|5/2/0|22/3/0|14|16/30|0/16|

La política aislada libera cinco negativos de training y conserva los cinco casos con errores conocidos. Después se cambió matching/riesgo: la exposición conjunta se evalúa al nivel de área y actividad de la fuente, diferenciándola de una afectación individual reportada. La reducción parcial de capacidad puede ser riesgo con entregas cubiertas y urgencia negativa. El intento3.2 exigía prueba de rutas individuales y perdió cinco asociaciones; se conserva en Git y no se adopta.

3.3 recupera el servicio marítimo declarado y no omite asociaciones de referencia en training, pero añade tres falsas asociaciones (dos de criticidad alta, ninguna fuente única). Su acción sigue siendo **verificar alcance**, no activar un alternativo o afirmar una entrega afectada. Dos falsas urgencias y una omisión de riesgo siguen revisadas. La mayor sensibilidad tiene coste de revisión y no se juzga solo por F1. El detalle operativo por noticia permanece en `reports/private/window-operational-errors.json`, fuera de Git y Docker.

## Comprobación nueva, congelada antes de consultar

24 sintéticos propios, fuente identificada, referencias razonadas antes de JEV: 18 puntuables y seis indeterminados. Los últimos no se etiquetan como verdaderos negativos; se comprueba revisión y ausencia de daño individual atribuido. Archivo reproducible: `window-final-controls.json`; protocolo y hashes: `window-final-evaluation-freeze.json`.

| 18 controles puntuables, incluidas revisadas | F1 riesgo | F1 urgencia | F1 proveedores | Revisión | Automáticos / errores |
|---|---|---|---|---|---|
|1.0.0|0,571|1,000|0,917|14/18|4/18 · 0/4|
|3.0 + revisión1.1|0,571|1,000|1,000|6/18|12/18 · 2/12|
|3.3 + revisión1.2|0,889|1,000|0,897|6/18|12/18 · 0/12|

Sobre las24entradas completas, la candidata automatiza12/24 y revisa12/24. La tabla usa18referencias completas; los otros seis son indeterminados, no verdaderos negativos. La candidata automatiza correctamente cuatro controles urgentes y dos identidades positivas. Conserva dos omisiones de riesgo (reducción parcial y ralentización menor) y tres asociaciones adicionales ante transporte continental sin rutas de fabricantes documentadas; todos revisados. Los seis controles indeterminados quedan revisados y no se presentan como afectación individual reportada. El perfil3.0 produjo un HTTP400 en uno de esos seis: 25 candidatos, 325 preguntas, 352446 bytes; causa exacta no comunicada por la API. No se repitió ese payload. La candidata compacta completó el mismo control. No se convierte el error en N ni se incluye una referencia inexistente en precisión.

La comprobación controlada cumple las guardas definidas, pero **no demuestra generalización independiente a RSS**. S003 continúa con provincia desconocida. La recuperación sintética de S024 no demuestra por sí sola que N044 quede resuelto; N044 no se utilizó para desarrollar. A06 permanece abierto.

## Consumo y límites

322 peticiones locales nuevas:17 exclusión relativa,82 intento3.2,40 potencial3.3,168 comparación congelada y15 en dos intentos adicionales descartados.321HTTP200/1HTTP400 diagnosticado; cero reintentos. Contador conservado **595→917**. Se reutilizaron A/B y verificaciones solo mediante igualdad del payload efectivo y validación del contrato; los reintentos mantienen su run_key y contador. Uso reportado por API, latencias y reutilización por ensayo en `window-candidate-results.json`; cuerpos y respuestas completas privados. El techo técnico de esta ventana es1500intentos, no una obligación de consumo.

No se consultaron validation, test, LiveDay ni answer key para iterar. La comparación histórica2.2 tiene el confusor de preceder al extractor1.1; no se atribuyen sus diferencias solo a matching. RSS periódico de pago permanece desactivado. Ninguna segunda respuesta del mismo modelo/fuente se llama corroboración externa independiente.

## Corrección de transporte y contexto RSS

En el primer recorrido real de esta ventana, A respondió200 y B400 sobre la noticia de tarifas Asia–Europa. Dos peticiones quedaron registradas; se detuvo el lote. No se convirtió el error en negativo. El extractor había unido5365caracteres del artículo, un ticker y noticias vecinas. La selección de un contenedor editorial devuelve3438caracteres de la noticia propia, comprobados con el HTML público respetando robots. Se conserva el snapshot anterior en PostgreSQL.

`fanout-1.0.0` mantiene completas las preguntas y el estado, pero reparte el mapa de preguntas independientes en cuerpos de hasta60000bytes. Reutiliza respuestas completas válidas antes de fragmentar, agrega respuestas con procedencia explícita y conserva los cuerpos/respuestas de cada grupo. No modifica el modelo1.13, umbrales o fórmula, ni activa el header de contexto ampliado. La [documentación oficial de modelos](https://docs.typesafe.ai/models) distingue64ktokens por petición y32k por pregunta; no fija una cantidad máxima de preguntas. El presupuesto en bytes es conservador y no pretende ser un tokenizer exacto. Los [límites del contrato](https://docs.typesafe.ai/api) se validan antes de enviar. Un estado/pregunta indivisible demasiado grande queda en error visible, nunca truncado niN.

Hay una guarda operativa de36intentos por generación/artículo, persistida y comprobada antes de cada llamada; convive con el deadline de60segundos y tres intentos por etapa/grupo. No es una autorización ni un presupuesto monetario nuevo. Las versiones quedan fijadas al encolar. Recuperar un trabajo con versión anterior crea una ejecución nueva mediante diagnóstico explícito, conservando el error, resultados e intentos previos. La API de diagnóstico es exclusiva del presentador y no captura headers ni credenciales.

La regresión desde cachés reproduce60casos (30training,6sintéticos anteriores,24controles propios):141etapas cacheadas y60respuestasA con hash efectivo comprobado;0peticiones nuevas, contador902→902. Predicciones, prioridades y revisión permanecen idénticas. Esto no es una evaluación nueva ni demuestra invariancia estadística de respuestas futuras; la partición conserva cada proposición y el mismo estado por pregunta, y se prueba aparte con mocks. La lectura RSS sí cambia cuando se corrige un contexto contaminado; se registran versión de extractor, hash y fecha real de consulta.


## Ensayos adicionales y decisión final

Se conservan como desarrollo, separados del perfil operativo:

- **risk-focus1.0 / decision3.4:**6 peticiones. Separó amenaza de stockout e inventario; sobre training mantuvo14 revisadas y16 automáticas sin reparar la omisión de riesgo. En los18 controles previamente inspeccionados pasó de12 a13 automáticos, sin errores entre ellos. El cambio no justificó una etapa adicional de pago ni una promoción.
- **risk-focus1.1 / review1.3:**9 peticiones. Permitió partir de asociación acreditada por el soporte ya existente y preguntó si la amenaza seguía actual, para localizar la duda activo/seguimiento. No recuperó omisiones ni mejoró cobertura. La propia pregunta sobre actualidad quedó incierta en amenazas limitadas o estratégicas. Se descarta; no se bajan umbrales para hacerla pasar.
- Una corrección posterior de serialización utiliza el enum de revisión ya permitido.60 casos reproducidos exclusivamente desde caché,110 etapas reutilizadas,0 peticiones nuevas, contador917→917; predicciones, prioridades y revisión idénticas. El supuesto camino de resolución también valida el contrato estricto en una prueba sintética. No se presenta como mejora del clasificador.

Los24 controles ya inspeccionados pasan a ser desarrollo para cualquier candidato posterior. Su comparación original de3.3 permanece congelada; no se anuncia otra evaluación independiente. **Se mantiene3.3/revisión1.2 como única candidata operativa seleccionable y1.0.0 como predeterminada.** No hubo promoción ni requiere rollback de datos. Elegir1.0.0 afecta una ejecución nueva y conserva todo el historial.

## Recorrido real de esta entrega

Railway consultó las seis fuentes:2 respuestas200 y4 respuestas304 en el primer sondeo de la ventana.304 significa consulta real sin contenido modificado, no una noticia nueva. El worker terminó los dos análisis manuales preparados con3.3: fletes Asia–Europa en revisión, sin riesgo/urgencia ni proveedores vinculados; incendio forestal clasificado como tal, automático sin vínculo con la cartera. No hay referencias independientes de precisión para esosRSS.

El recorrido usó11 peticiones:2 del intento inicial fallido y diagnosticado,7 de la recuperación con contexto editorial correcto y2 del incendio.10HTTP200/1HTTP400,0 reintentos; contadorRSS49→60, separado del local. El incendio tardó4,42s desde clic hasta resultado visible. El tiempo exacto del clic de fletes no quedó persistido antes de fallar un selector del verificador; se conserva nulo y no se repite análisis válido para fabricar una medición.

La noticia de fletes sustenta una **consulta manual** a Oceanbridge con cita literal e hipótesis explícita: confirmar exposición comercial del servicio marítimo, sin afirmar entregas afectadas. Edición, guardado, copia con readback, TXT y reconexión están comprobados enRailway; no cambian clasificación, score ni alertas. El alternativo ferroviario necesita confirmar adecuación antes de disponibilidad/capacidad. Productos no mapeados sigue siendo un dato desconocido.

**Consumo total de esta ventana:**333 peticiones nuevas entre ambos entornos,331HTTP200/2HTTP400 diagnosticados y0 reintentos. No se suman sus contadores históricos entre sí. Uso reportado, duración y reutilización por ensayo enJSON; no se infiere saldo monetario. RSS periódico de pago permanece desactivado.
