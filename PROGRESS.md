# Progreso — Supplier Risk Radar

## Plan y estado (17-10-2026)
1. Base visible: PostgreSQL, Alembic, configuración segura, sesión, catálogo/importaciones y dashboard/ficha responsive.
2. Motor: dos etapas JEV, política de referencia, cola con leases, evidencias y exportación.
3. Continuidad: seis RSS reales, versiones, deduplicación e incidentes/recuperaciones.
4. Experiencia: filtros, analítica, alarmas, borradores y accesibilidad.
5. Integración: pruebas, auditoría A01–A20, imagen y preparación Railway.

## Lectura y decisiones
- Leídos README, docs, contratos, configuración, manifiesto y referencias de motor/preguntas. No se busca ni utiliza answer key.
- Se conserva `evidence/validation_report.json` modificado y el archivo no seguido preexistente; no pertenecen a esta entrega.
- TYPESAFE_API_KEY, ADMIN_PASSWORD, SESSION_SECRET: configuradas. DATABASE_URL: faltante; preparar PostgreSQL local y configuración separada sin cambiar `.env`.
- Uso de Railway y stack explícitos prevalece sobre el flujo de hosting Sites; no se crea un Site.
- El prompt actual sustituye aprobaciones antiguas. Publicación/push/recursos de pago requieren aprobación agrupada final.
- Contrato oficial consultado: https://docs.typesafe.ai/api y /models; endpoint /v1/systemone, versión fijada jev-1.13.0.

## Autorizaciones
- JEV: hasta 3 artículos de entrenamiento, dos etapas, máximo 2 reintentos; consumidos 0 artículos / 0 peticiones.
- RSS: consultas reales autorizadas; análisis periódico de pago desactivado.
- Pendientes: ampliar consumo para validación, test/LiveDay, RSS analizado y ensayo Railway; publicación y recursos externos.

## Siguiente tarea
Implementar y verificar la base sobre PostgreSQL, sin utilizar SQLite como sustituto de persistencia.

## Hitos verificados
- Base y catálogo: migraciones 0001–0002 sobre PostgreSQL 16.15; 40 proveedores, 20 materiales, 6 productos y lotes 30/10/20/14 importados idempotentemente. `.env` intacto.
- `npm --prefix frontend run build`: pasa. Dependencias con versiones exactas, lockfile; actualización tras avisos, último npm install informa 0 vulnerabilidades.
- `DATABASE_URL=…/radar_test .venv/bin/python -m pytest -q`: 29 pruebas pasan. Base dedicada y mocks identificados, sin llamadas de pago.
- `npm --prefix frontend run test:e2e`: 5 pasan; 360/390/768/1440 px sin overflow y filtro/foco de diálogo. Capturas en reports/.
- Referencia: 16 tests pasan. No se ha sobrescrito el informe de validación preexistente.
- RSS real local: seis HTTP 200, 37 versiones recientes (4/3/9/10/1/10). Evidencia en reports/rss-local.json. No probado desde Railway; inferencia RSS desactivada.
- JEV real local: N001, N002, N005; 4 peticiones HTTP 200, 0 reintentos; modelo devuelto jev-1.13.0; 1,476 s total. Detalle de uso en reports/jev-local.json. El cupo inicial queda consumido (3/3), también al desplegar otra base.
- Preguntas/política congeladas en reports/prompt-freeze.json antes de cualquier evaluación retenida. Validación/test/LiveDay sin inferencia.

## Correcciones comprobadas
- Etiquetas aisladas en payload efectivo; 40 Noul y etapa B agrupada para varios proveedores.
- Inventario null/0/no aplicable, exportación bloqueada ante error, caché/consumo duraderos, reclamación concurrente y lease vencida.
- Noticia tardía tras recuperación conservada sin reabrir incidente; ranking por máximo.
- Accesibilidad: nombre explícito en filtros y foco al abrir/cerrar diálogo.

## Limitaciones del entorno
- Sin Docker/CLI Railway. PostgreSQL descargado a /tmp y arrancado en localhost:55432 mediante escalación del sandbox; no se modificó el sistema ni `.env`.
- Pendientes: ensayo auditivo real, contenedor, Railway, ampliación de consumo y ensayo completo de 14 artículos. Las pruebas con mocks no acreditan precisión ni rendimiento del lote real.

## Siguiente tarea
Completar pruebas de borradores/audio, operación y documentación; auditoría A01–A20 y propuesta agrupada de publicación/consumo.
