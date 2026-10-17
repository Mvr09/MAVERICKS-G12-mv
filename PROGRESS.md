# Progreso · Supplier Risk Radar

Actualizado 17-10-2026. Código publicado en Railway; frontend accesible, base de datos/esquema remoto pendiente de diagnóstico. Primer commit de hito: `6e80b4e`. Se conserva el cambio previo de `evidence/validation_report.json` y el archivo no seguido preexistente.

## Plan y entregas
1. **Hecho:** PostgreSQL/Alembic, configuración segura, sesión/CSRF/permisos, importación idempotente y catálogo; dashboard/ficha responsive.
2. **Hecho:** cliente JEV oficial en dos etapas, contrato Pydantic/JSON Schema, evidencias, política de referencia, cola con leases/heartbeat y exportación.
3. **Hecho:** seis RSS reales, estados/ETag/304, versiones, deduplicación, incidentes, recuperación e historia. Análisis RSS real pendiente de presupuesto.
4. **Hecho:** filtros, proveedor/material/productos, analítica, alertas visuales/lógica sonora, borradores editables, copia/TXT y resolución motivada.
5. **Preparado:** Dockerfile no privilegiado, Compose, Railway web/worker, README y paquete permitido. Auditoría A01–A20 en reports/AUDITORIA.md.

## Evidencia y comandos ejecutados
- Lectura inicial: README, docs/, config/, contracts/, referencias, manifiesto y prompts de diseño/auditoría. No se buscó ni abrió answer key ni se exploraron XLSX ajenos al manifiesto.
- `alembic upgrade head`: migraciones 0001–0002; esquema de 17 tablas comprobado en base independiente nueva. PostgreSQL 16.15 local en 127.0.0.1:55432 (binarios en /tmp).
- `app.cli import-manifest`: 40 proveedores, 20 materiales, 6 productos; lotes 30/10/20/14; originales intactos. Repetición idempotente.
- `DATABASE_URL=…/radar_test .venv/bin/python -m pytest -q`: **36 pasan**. Base desechable independiente, mocks identificados; sin llamadas de pago.
- `python -m unittest discover -s reference -p 'test_*.py' -v`: **16 pasan**. No se sobrescribió el informe de validación del usuario.
- `npm --prefix frontend run build`: pasa; dependencias exactas y lockfile, gráficos separados. Última instalación npm: 0 vulnerabilidades informadas.
- `E2E_URL=…:8001 E2E_FULL=1 npm --prefix frontend run test:e2e`: **8 pasan**, mocks identificados. Carga, borrador, guardado/copia/TXT, exportación, foco y lógica de audio.
- `npm --prefix frontend run test:e2e -- responsive.spec.ts`: **5 pasan** con datos locales reales, 360/390/768/1440 px; resumen, ficha, noticias, fuentes, analítica y material sin overflow. Capturas en reports/. Chrome emulado; no móvil físico.
- `scripts.smoke http://127.0.0.1:8000`: salud/listados/ruta profunda 200, secretos/originales 404, mutación pública 401.
- `scripts.check_restart`: sesión, 40 proveedores, 74 entradas y 3 análisis sobreviven al reinicio real de web.
- `scripts.check_worker`: seis trabajos RSS completados, reinicio conservado, peticiones JEV antes/después = 4/4; reports/worker-local.json.
- `scripts.package_deploy`: paquete permitido en .runtime/deploy y tar.gz; revisión de secretos del frontend/paquete pasa. Sin originales, etiquetas o .env. Docker no disponible: build de imagen no ejecutado.

## Pruebas externas y autorización consumida
- Credenciales TYPESAFE_API_KEY, ADMIN_PASSWORD, SESSION_SECRET configuradas; no se muestran, regeneran ni modifica `.env`. DATABASE_URL faltaba; configurada por proceso para ensayos locales.
- JEV real: **3/3 artículos consumidos**, N001/N002/N005; **4 HTTP 200**, 0 reintentos; versión devuelta jev-1.13.0; **1,476 s** total local. Uso en reports/jev-local.json. No se extrapola a LiveDay.
- config/authorization.json conserva el cupo agotado también en una base nueva. Nuevos grants solo tras autorización explícita; cuatro llamadas simultáneas globales y hasta tres intentos por etapa.
- RSS real local: **6/6 HTTP 200**, 37 versiones recientes en la consulta inicial; reportado en reports/rss-local.json. No consultado desde Railway. Análisis de pago desactivado, noticias pendientes.
- Preguntas/política congeladas en reports/prompt-freeze.json. Validación, test y LiveDay importados, **sin inferencia** ni métricas inventadas.

## Correcciones de auditoría
Etiquetas excluidas del payload HTTP, 40 candidatos, etapa B múltiple, inventario null/0/no aplicable, prioridad independiente de confianza, máximo de incidentes, recuperación posterior y noticia antigua; caché parcial distinguida; versiones RSS pendientes sustituidas; errores no convertidos en N. Reintento con diagnóstico conserva presupuesto. Bandas numéricas de UI obtenidas de la política de API. Foco de diálogo, filtros móviles y cooldown sin reproducir historial probados.

## Pendientes y siguiente acción
- Código publicado por push autorizado a main: 365bb4c. URL pública https://mavericks-g12-mv-production.up.railway.app; frontend/health/assets HTTP 200, readiness 503 y catálogo/fuentes 500.
- No hay acceso directo Railway: el usuario opera el panel. GitHub confirma autodeploy en peaceful-harmony / production. Log Deploy recibido: DATABASE_URL apunta a localhost. Requiere referencia a PostgreSQL remoto; no se solicita token Railway.
- Propuesta única en reports/APROBACION_PENDIENTE.md: una ventana de 45 min, hasta 83 artículos adicionales (27 training, 10 validation, 20 test, 14 LiveDay, 12 RSS), máximo 498 peticiones, reintentos incluidos.
- Pendientes: build Docker, evaluación retenida, RSS analizado en Railway, exportación final y LiveDay ≤300 s medidos; audibilidad y móvil físico. Auditoría marca explícitamente lo no ejecutado; no hay aceptación completa.
- Próxima acción dependiente: revisar logs de Deploy/Pre-deploy y corregir conexión PostgreSQL o migraciones según la evidencia. El usuario ya corrigió APP_BASE_URL y ejecutó redeploy. No se amplía consumo JEV; RSS de pago permanece false en la API pública.

## Continuación: autodeploy existente (17-10-2026)
- Usuario autoriza push al repositorio conectado; no hay acceso Railway ni autorización adicional de inferencia. Rama main confirmada por el usuario; variables pegadas por el usuario en Railway, valores remotos no accesibles desde esta sesión.
- `git fetch`, `git ls-remote`: GitHub main en 1c5e149; 6e80b4e y d527d30 aún locales. GitHub muestra deployment fallido en peaceful-harmony / production para 1c5e149.
- URL aportada: https://mavericks-g12-mv-production.up.railway.app, target port 8000. A las 18:48 UTC, /, /healthz, /readyz, catálogo y config devuelven 404 de Railway «Application not found».
- Corrección preparada: railway.json predeterminado, entrypoint común python -m app.web con bind 0.0.0.0:8000; web/config/Docker coherentes, migraciones y seed en predeploy, RSS de pago false por defecto. /healthz identifica RAILWAY_GIT_COMMIT_SHA cuando está disponible.
- Build frontend pasa; suite PostgreSQL local ampliada: 38 pruebas pasan. Sin nuevas llamadas a JEV ni grants.
- Pasos exactos de panel y logs necesarios: docs/09_AUTODEPLOY_EXISTENTE.md. Siguiente: confirmar rama, revisar/commitear y hacer push autorizado; comprobar URL y assets tras autodeploy.

- Verificación adicional: entrypoint arrancado con PORT=12345 y escucha observada en 0.0.0.0:8000; smoke local pasa. Consumo PostgreSQL de demo: 4 peticiones JEV, grant inicial 3/3, RSS de pago desactivado. Rama main confirmada; push autorizado ejecutado a continuación.

- Push ejecutado: origin/main avanzó de 1c5e149 a 365bb4cfca506e3d6d34a8a8b1ecd588f9834a2e. GitHub registra «Railway is deploying the service» (pending). Se espera comprobación pública; no se interpreta el push como éxito del servicio.
- Recordatorio de panel: APP_BASE_URL debe ser el HTTPS público; DATABASE_URL debe referenciar PostgreSQL remoto, no estar vacía ni ser localhost. No se han consultado ni divulgado los valores remotos.

## Resultado publicado y comprobación posterior al panel
- Push confirmado en GitHub y URL: **365bb4cfca506e3d6d34a8a8b1ecd588f9834a2e**. GitHub pasó pending → success entre 18:59:13 y 18:59:44 UTC. /healthz confirma ese SHA.
- Comprobación completa 18:59:51 UTC y repetición tras el redeploy indicado por el usuario (19:00:39 UTC): / 200, /healthz 200, /readyz 503, /api/suppliers 500, /api/sources 500, /api/config 200; cuatro assets JS/CSS 200 con MIME correcto. RSS de pago false. **No hay aceptación completa**: catálogo remoto no verificable.
- Evidencia: reports/autodeploy-365bb4c.json, reports/public-deployment-365bb4c.json y reports/public-deployment-after-panel-redeploy.json. No se afirma éxito de base de datos por el estado Deployed.
- Solicitadas últimas 80 líneas de Deploy/Pre-deploy (Alembic, seed y primer error SQLAlchemy/psycopg), con secretos ocultos. Build no es el bloqueo observado. Revisar DATABASE_URL de PostgreSQL remoto y ejecución de predeploy según docs/09_AUTODEPLOY_EXISTENTE.md.
- Los informes posteriores al push y este seguimiento se conservan localmente; no se dispara otro autodeploy solo para registrar el diagnóstico. Los dos cambios preexistentes del usuario siguen excluidos.

## Log recibido: causa confirmada y corrección
- El log de Deploy apunta a localhost/127.0.0.1/::1:5432 con connection refused; no hay conexión a PostgreSQL remoto. El límite de 500 logs/s se alcanza por tracebacks repetidos en las consultas de la UI.
- Implementado bloqueo de loopback en Railway, errores JSON 503 sanitizados para configuración/conexión/esquema y backoff de sondeo de 30 s en fallos; consulta inmediata al recuperar foco. Sin cambios en datos ni presupuesto JEV.
- Pruebas backend: 44 pasan; build TypeScript/Vite pasa. Preparado ensayo de navegador con mocks para recuperación y ausencia de promesas rechazadas.
- Acción necesaria del usuario: DATABASE_URL debe ser referencia al PostgreSQL del mismo entorno; revisar predeploy Alembic + seed y healthcheck /readyz. Pasos exactos añadidos a docs/09_AUTODEPLOY_EXISTENTE.md. El arreglo de logs no sustituye esta configuración remota.

- Playwright: **9/9 pasan** en Chromium, incluidos 360/390/768/1440 px, teclado, audio simulado y backoff ante 503 (25 s sin repetir, reintento posterior). No demuestra audibilidad física. Revisión de origin/main confirma 365bb4c antes del nuevo push; se excluyen cambios ajenos y capturas regeneradas.
