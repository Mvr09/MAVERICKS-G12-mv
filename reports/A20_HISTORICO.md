# A20 · medición histórica y separación de LiveDay

## Qué se ejecutó y cuándo

- Fecha: **17-10-2026**, durante la fase final autorizada original, después de congelar preguntas/política.
- Commit de ejecución: **4a3645ae1a51084f2134762f41c0210efbe48668**.
- Modelo: **jev-1.13.0**. Perfil/preguntas y política: **1.0.0**.
- LiveDay: **14 entradas y14filas exportadas**, IDs únicos, orden conservado, columnas requeridas y RSS excluido.
- Inicio registrado por el cliente: **21:28:35.424566 UTC**.
- Exportación recibida por el mismo cliente: **21:28:41.177534 UTC**.
- Diferencia registrada: **5,753s**, inferior al límite300s. Incluye espera de cola, inferencia y recepción del Excel según el recorrido del runner.

El runner comprueba que el lote no tenga filas ya terminadas antes de una medición nueva. El historial de llamadas registra **14peticiones A nuevas para14News_ID distintos y9peticiones B nuevas**,23HTTP200 en primer intento. **No fue un replay íntegramente cacheado.** El artefacto consultado no conserva flags de caché por análisis: no se afirma una ausencia absoluta de caché para cada etapaB solo porque no aparezca una petición. No se vuelve a abrir el archivo/exportación para reconstruir ese dato.

## Método de reloj y límites

El tiempo5,753 procede de restar dos `datetime.now(timezone.utc)` del mismo cliente en scripts/final_rehearsal.py, **no de un cronómetro monotónico**. Los timestamps del servidor fueron21:28:09.954112→21:28:13.821974(3,867862s); había una diferencia de reloj cliente/servidor de aproximadamente26s. No se resta un timestamp de un sistema al del otro ni se sustituye el tiempo end-to-end por tiempo de procesamiento del servidor. No consta un salto del reloj del cliente en ese intervalo, pero el método no ofrece la garantía de un reloj monotónico.

El lote ya se ejecutó en esa fecha: «test/LiveDay no ejecutados» en los metadatos originales de congelación describía el momento **anterior** al ensayo, no el estado posterior. En esta consolidación solo se leyeron metadatos de ejecución ya guardados, sin celdas, etiquetas ni nuevas predicciones de LiveDay.

## Qué acredita hoy

Acredita el resultado histórico del commit/perfil citados. Exportaciones/celdas y persistencia se verificaron después en53593e2, sin inferencia nueva. Los cambios de duración posteriores introducen candidatos nuevos enB; las preguntas del default siguen congeladas, pero eso **no convierte5,753s en una medición de12c4dff**. Tampoco mide el experimental2.2.0 ni desempeño del clasificador.

Por ello la matriz actual registra **A20 no ejecutado para12c4dff, con antecedente histórico aprobado**. Si se exige una nueva aceptación de rendimiento de la versión final, ejecutar ese ensayo únicamente en su fase final autorizada y medir con cronómetro monotónico, incluyendo reintentos. No usar sus salidas para modificar prompts, umbrales, asociaciones o catálogo. No se repite ahora, no se ajusta con sus resultados y no se declara nueva evaluación independiente.

Evidencia: final-execution-summary.json; metadatos privados del ensayo final; resumen sin respuestas en a20-historical-evidence.json. El código del runner se inspeccionó, no se ejecutó.
