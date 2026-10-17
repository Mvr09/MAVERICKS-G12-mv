# Auditoría A01–A20 · 17-10-2026

Revisión de la aplicación conforme a `prompts/03_AUDITORIA_Y_ENTREGA.md`. Los resultados de mocks no se presentan como exactitud de JEV ni como aceptación de Railway. No se abrió ni buscó el answer key. No se ejecutó inferencia de validación, test o LiveDay.

| ID | Estado | Evidencia y límite |
| --- | --- | --- |
| A01 | pasa | PostgreSQL: 40 Suppliers, 20 Materials, 6 productos; prueba del payload efectivo con 40 preguntas Noul. |
| A02 | pasa | Importaciones explícitas News/News_Validation/News_Test/News_Feed: 30/10/20/14 filas; hash/idempotencia y diagnósticos probados. Originales intactos. |
| A03 | pasa | `test_effective_payload_label_isolation_and_multisupplier` inspecciona el cuerpo HTTP enviado al transporte simulado: sin las cinco etiquetas ni centinela. |
| A04 | no ejecutado | Caso de homónimo cubierto con mock e ingreso por los 40 candidatos; falta evaluación real retenida autorizada. No se afirma precisión semántica. |
| A05 | no ejecutado | Test integrado positivo conserva ID y fuerza N/N/0 con mock. Pendiente comprobar la clasificación real del conjunto retenido. |
| A06 | no ejecutado | Selección múltiple y etapa B agrupada probadas con mocks. La exactitud del alcance regional real requiere evaluación autorizada. |
| A07 | pasa | Prueba integrada de duplicado y evento distinto: historial compartido, dos incidentes cuando corresponde y ranking por máximo. Agrupación conservadora; ambiguos a revisión. |
| A08 | pasa | Recuperación compatible posterior cierra solo su incidente, retiene máximo histórico y una noticia anterior recibida tarde no lo reabre (integración con mock). |
| A09 | pasa | Null físico → revisión; servicio no aplicable omite buffer; cero real → presión máxima. Pruebas propias y de referencia. |
| A10 | pasa | Motor usa `reference/scoring.py`, política 1.0.0 y redondeo half-up; 16 tests de referencia y pruebas de integración. Confianza separada de gravedad. |
| A11 | no ejecutado | Las seis fuentes dieron HTTP 200 localmente (37 versiones recientes). `rss-local.json` y `worker-local.json`. Falta consulta desde Railway y análisis RSS real autorizado. |
| A12 | pasa | RSS repetido, edición del mismo GUID, versiones, 304 y XML peligroso probados con transporte simulado; nunca se fabrican artículos en el flujo real. |
| A13 | pasa | Mocks 400/401/422: un intento y error/null; 429/529/503: hasta tres intentos; contrato/distribuciones/modelo incorrectos rechazados; exportación bloqueada ante error. |
| A14 | no ejecutado | E2E pasa gesto, prueba, historial silencioso, una emisión, cooldown 30 s, foco, mute, título y bloqueo. Falta audibilidad en dispositivo físico. |
| A15 | pasa | E2E con mocks identificados: consulta al alternativo, edición, guardado, copia y TXT. Texto declara stock sin confirmar y no constituye pedido. Sin integración externa de envío. |
| A16 | no ejecutado | Exportación XLSX sintética probada: una fila por entrada, IDs ordenados con `; `, tipos texto y bloqueo por error; falta exportación de test/LiveDay con inferencia final autorizada. |
| A17 | no ejecutado | Reinicio real local conserva sesión, 40 proveedores, 74 artículos y 3 análisis; worker reiniciado sin ampliar JEV; claim concurrente/lease probado. Falta redeploy Railway. |
| A18 | no ejecutado | Lectura pública, CSRF, permisos y bloqueo de originales/secretos probados localmente; empaquetado permite solo archivos revisados. No existe aún URL HTTPS pública. |
| A19 | pasa | Chrome/Playwright, emulación 360/390/768/1440 px; sin overflow, filtros con teclado y foco de diálogo. Capturas en reports. Pendiente móvil físico; no se presenta emulación como dispositivo real. |
| A20 | no ejecutado | LiveDay sin inferencia. No hay tiempo medido del lote de 14 en Railway. Los 1,476 s de la comprobación de tres artículos no se extrapolan. |

## Pruebas realizadas

- 36 pruebas propias unitarias/integración sobre PostgreSQL dedicado `radar_test`, con mocks identificados.
- 16 tests de referencia, sin llamadas externas.
- 8 E2E sobre servidor separado con banner de mocks: catálogo/ficha en cuatro anchuras, teclado, borradores/carga/exportación y lógica de audio.
- Build TypeScript/Vite correcto; dependencias frontend fijadas y última instalación sin vulnerabilidades reportadas por npm.
- JEV autenticado local: N001/N002/N005; cuatro HTTP 200, cero reintentos, modelo devuelto `jev-1.13.0`. Solo se registra metadato de ejecución, no respuestas protegidas.
- RSS real local: seis HTTP 200; estados/fallos aislados, últimas consultas y artículos pendientes persistidos. No se acredita disponibilidad desde Railway.
- Migraciones desde una base independiente nueva, sesión tras reinicio real y worker sin consumo de JEV adicional.

## Pendientes bloqueantes para aceptación completa

Autorización de despliegue y acceso Railway; build real de contenedor (Docker no instalado aquí); grants concretos para evaluación y fase final/RSS; ensayo HTTPS/redeploy y fuentes desde Railway; lote LiveDay completo medido ≤300 s; audibilidad y uso en dispositivo real. No se declara aceptación completa.
