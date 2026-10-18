> **Informe histórico del17-10-2026.** Estado y pendientes de la versión actual en [ACEPTACION_ACTUAL.md](ACEPTACION_ACTUAL.md). No interpretar sus tiempos o versiones como una ejecución nueva.

# Informe de ejecución y entrega · 17-10-2026

## Publicación

Aplicación real: https://mavericks-g12-mv-production.up.railway.app. Web, worker y PostgreSQL operativos. Versión publicada **53593e2**, verificada a las 21:44:43 UTC con HTTP 200 en /, /healthz, /readyz, catálogo y cuatro assets. Web y worker coinciden en revisión. Escucha web 0.0.0.0:8000, esquema 0004. La ejecución final se realizó con el código 4a3645a, modelo jev-1.13.0, preguntas y política 1.0.0 congeladas. No se consultó el answer key ni se reajustaron reglas con datos retenidos.

## Lotes medidos en Railway

| Lote | Artículos | Tiempo hasta Excel recibido | Peticiones registradas |
| --- | ---: | ---: | ---: |
| Validación | 10 | 670,043 s | 18 |
| Test | 20 | 5,763 s | 30 |
| LiveDay | 14 | **5,753 s** | 23 |

LiveDay cumple el máximo de 300 s, incluyendo encolado, procesamiento y descarga. No se extrapola desde mocks ni RSS. Validación incluye dos intentos rechazados por una comprobación local de Score más estricta que el esquema oficial y la pausa de diagnóstico; no es una medición de latencia normal del modelo. El score devuelto se conserva; no se recalcula con probabilidades publicadas.

Exportaciones reales (requieren sesión de presentador): [validación](https://mavericks-g12-mv-production.up.railway.app/api/batches/73440b8a-60c2-4cbf-a0ca-71eaea21d540/export.xlsx), [test](https://mavericks-g12-mv-production.up.railway.app/api/batches/5dd24227-0ae6-4614-b160-30f51ca0afe5/export.xlsx), [LiveDay](https://mavericks-g12-mv-production.up.railway.app/api/batches/e180cc6d-3cba-4352-8d12-799152db6561/export.xlsx). Copias privadas en `.runtime/final/`. Verificados número y orden de filas, News_ID único, Y/N, IDs únicos/ordenados y delimitador `; `. Test conserva columnas originales. No contienen RSS ni fixtures ni etiquetas de evaluación.

## Evaluación retenida: 10 noticias

| Métrica | Precisión | Recall | F1 | Denominador |
| --- | ---: | ---: | ---: | --- |
| Riesgo | 100 % | **60 %** | 0,750 | 5 positivos, 5 negativos |
| Urgencia | 100 % | 100 % | 1,000 | 2 positivos, 8 negativos |
| Proveedores (micro) | 100 % | 70 % | 0,824 | 10 asignaciones esperadas |

Conjunto de proveedores exacto: **8/10** noticias. Requieren revisión: **8/10**. Se observaron dos falsos negativos de riesgo; esta muestra no acredita cobertura completa ni uso autónomo. Dos noticias positivas conservaron identidad sin riesgo/urgencia; un caso negativo con coincidencia de nombre no creó vínculo. En los dos casos con varios proveedores, solo uno obtuvo el conjunto exacto: A06 queda fallido en el ensayo retenido. Se conserva el resultado y no se retocan prompts para hacerlo pasar.

No hay métricas de exactitud de test/LiveDay porque no se usaron respuestas protegidas ni answer key. Informe detallado en `reports/private/final-rehearsal.json` y auditoría de escenarios en `reports/private/validation-scenario-audit.json`, excluidos de Git y del frontend.

## RSS y consumo

Seis fuentes realmente consultadas desde Railway con HTTP 200/304 y errores aislados visibles. Las 37 noticias recibidas están procesadas: **23 en revisión, 14 completadas**, sin pendientes ni errores actuales. El contexto indica exposición potencial de una cartera simulada. RSS no altera las exportaciones del ejercicio.

Presupuesto nuevo: **100/200 peticiones consumidas**, incluidos fallos y reintentos. Restan 100 hasta el cierre de la ventana original (22:01:52 UTC); no se renueva al desplegar. Inferencia periódica de pago desactivada; consultas RSS gratuitas siguen cada cinco minutos. Cupos anteriores de training y RSS agotados y conservados. El uso numérico reportado se registra por intento; falta el uso de una respuesta fallida inicial, sin estimar coste.

## UI y operación verificadas

62 pruebas backend/runner pasan al cierre; 33 regresiones dirigidas tras la corrección del adaptador; 13 E2E con mocks identificados. Build y migración desde base nueva pasan. Navegador real contra Railway sin mocks: borrador al alternativo con fragmento validado, edición/guardado, copia y TXT sin envío; endpoint privado 401 al cerrar sesión; sin errores JS ni overflow a 360/390/768/1440 px. Evidencia `final-ui-real.json`.

Tras el último redeploy se compararon todas las celdas de las tres exportaciones: idénticas, HTTP 200. Persisten 44 resultados de ejercicio, 37 RSS y consumo 100/200; cero nuevas llamadas en la comprobación. Evidencia `final-delivery-verification.json` y `public-deployment-final.json`.

La limpieza de Entrenamiento/LiveDay no se ejecutó en Railway. Mantiene vista previa y confirmación explícita; conserva catálogo, RSS, evaluación y consumo.

## Pendientes de aceptación

- **A06 falla** en un caso retenido de selección múltiple. Una mejora futura exige desarrollo con entrenamiento y nueva evaluación, sin ajustar sobre este resultado de validación/test/LiveDay.
- **A14 pendiente solo de metadatos del ensayo**: el usuario confirma «funciona perfecto» para activar/probar/silenciar/probar en la versión publicada; falta indicar dispositivo y navegador. Playwright acredita lógica, no sonido físico.
- Móvil físico omitido por decisión del usuario. No se declara probado.

La aplicación está desplegada y el ensayo LiveDay completado; no se declara aceptación completa mientras persistan estos puntos.
