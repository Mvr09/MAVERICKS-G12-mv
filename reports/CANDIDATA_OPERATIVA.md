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

307 peticiones locales nuevas: 17 exclusión relativa, 82 intento3.2, 40 potencial3.3, 168 comparación congelada. 306HTTP200/1HTTP400 diagnosticado; cero reintentos. Contador conservado **595→902**. Se reutilizaron A/B y verificaciones solo mediante igualdad del payload efectivo y validación del contrato; los reintentos mantienen su run_key y contador. Uso reportado por API, latencias y reutilización por ensayo en `window-candidate-results.json`; cuerpos y respuestas completas privados. El techo técnico de esta ventana es1500intentos, no una obligación de consumo.

No se consultaron validation, test, LiveDay ni answer key para iterar. La comparación histórica2.2 tiene el confusor de preceder al extractor1.1; no se atribuyen sus diferencias solo a matching. RSS periódico de pago permanece desactivado. Ninguna segunda respuesta del mismo modelo/fuente se llama corroboración externa independiente.
