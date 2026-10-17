# Supplier Risk Radar · seguimiento

## Estado actual · 17-10-2026
- Publicado por push autorizado a `origin/main`: **8477e5b5411e892b2436923fbc195e821859c904**. Repositorio Mvr09/MAVERICKS-G12-mv; Railway peaceful-harmony / production. No hay acceso directo al panel.
- URL real: https://mavericks-g12-mv-production.up.railway.app. Comprobación 20:39:01 UTC: /, /healthz, /readyz, catálogo, fuentes, config y cuatro assets **HTTP 200**; SHA coincide, esquema **0003**, **40 proveedores**, **20 materiales**, **6 fuentes**. Catálogo conservado después del autodeploy.
- RSS remoto confirmado: **worker conectado**, seis fuentes consultadas realmente desde Railway (200/304, sin errores actuales), **37 artículos** persistidos. Lote autorizado completado: 10 artículos (1 done, 9 review), 27 pendientes.
- Cupo adicional autorizado por el usuario: **10 noticias RSS / máximo 60 peticiones JEV**, reintentos incluidos. Grant `rss-demo-20261017-10`, límite persistente, vencimiento de seguridad 19-10-2026 00:00 UTC. Verificado remoto: **0 disponibles, 10 reservados/consumidos, 10 peticiones RSS nuevas**, sin caché ni reintentos; modelo jev-1.13.0. **6,964 s** medidos desde solicitud hasta trabajos terminados. Inferencia periódica **false**.

## Implementación y correcciones
- React/TS/Vite/Tailwind, FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL; web y worker usan misma imagen. Web escucha 0.0.0.0:8000 conforme al dominio existente. Sesión presentador, CSRF, lectura pública normalizada, originales/secretos no públicos.
- Importador explícito de cuatro Excel del manifiesto, hash/idempotencia y diagnósticos; etiquetas de evaluación separadas. Originales intactos, sin buscar/abrir answer key. 40 identidades evaluadas por Noul y dos etapas de referencia; preguntas/política congeladas.
- Cola PostgreSQL con claim transaccional, leases, heartbeat y límites; caché e intentos durables. RSS deduplicado/versionado, incidentes agrupados y recuperaciones conservadoras; prioridad máxima por proveedor. Exportación no convierte errores en N.
- Despliegue corregido desde 365bb4c y bb39a08. Log recibido confirmó localhost:5432 por DATABASE_URL vacía; usuario corrigió la conexión PostgreSQL remota. Guard loopback, errores 503 sanitizados y backoff UI de 30 s evitan tracebacks repetidos. Se verificó recuperación de readiness.
- Ampliación pedida: **Materiales** en sidebar, listado/búsqueda/categoría, fichas con datos disponibles y proveedores; Noticias filtra por fuente y lote. RSS muestra progreso real, cola, errores, worker y stream de incorporaciones. «Silenciar» también bloquea «Probar alarma».
- Predeploy preparado: `python -m app.predeploy` ejecuta migración + seed secuencialmente. Migración 0003 añade presencia de worker. El sync manual y arranque de worker también inicializan seis fuentes/cupos idempotentemente; el sync manual remoto lo ha comprobado.
- **Preparar demo**: vista previa y confirmación explícita LIMPIAR DEMO para retirar solo training/LiveDay y dependencias exclusivas. Conserva catálogo, RSS, validation/test, caché y consumo. Bloquea trabajo activo, cambios desde preview e incidentes compartidos. **No ejecutado en Railway**.

## Pruebas y evidencia
- **51 unitarias/integración** sobre PostgreSQL dedicado `radar_test`: pasan; única advertencia de deprecación Anyio externa. Incluyen payload efectivo sin las cinco etiquetas, permisos/CSRF, importación, decisión, cola, preservación de consumo y limpieza acotada, fallos y circuito de diagnóstico.
- **13 E2E Chromium** con mocks identificados: pasan. 360/390/768/1440 px, teclado, materiales, progreso RSS, borrador/TXT, carga/exportación, audio lógico/cooldown/foco/bloqueo y cancelación de limpieza. Capturas de materiales revisadas visualmente. Usuario confirma fichas, persistencia tras recarga y tono audible de versión previa; omite móvil físico. Audibilidad corregida pendiente de ensayo físico.
- Build TypeScript/Vite: pasa. Migración 0003 desde 0002: pasa, 18 tablas. `app.predeploy` completo sobre base aislada: pasa. Paquete permitido: 52 archivos, sin originales ni secretos. Build Docker ejecutado por Railway; Docker local no disponible.
- Suite de referencia: 16 pasan, sin llamadas externas. JEV real inicial: **3/3 training consumidos**, N001/N002/N005, **4 HTTP 200**, sin reintentos, modelo devuelto jev-1.13.0, **1,476 s local**. No se extrapola a 14 artículos.
- RSS real local previo: **6/6 HTTP 200**, 37 versiones recientes iniciales; reports/rss-local.json y worker-local.json. Los resultados locales no se presentan como consultas de Railway.
- Comandos: `npm --prefix frontend run build`; `DATABASE_URL=<base radar_test> .venv/bin/python -m pytest -q`; preparación `python -m tests.setup_e2e` y `E2E_URL=http://127.0.0.1:8001 E2E_FULL=1 npm --prefix frontend run test:e2e`; `python -m scripts.check_migrations`; `python -m scripts.package_deploy`; `python -m scripts.check_public_deployment --expected-commit <SHA>`.
- Evidencia posterior al push conservada localmente: reports/public-deployment-8477e5b.json, rss-railway-after-sync.json y railway-ui-8477e5b.json. No disparar otro autodeploy solo para registrar observaciones.

## Autorización, seguridad y cambios ajenos
- Push a main autorizado expresamente para este proyecto; commits revisados sin secretos ni cambios ajenos. Se preservan evidence/validation_report.json y el archivo ajeno sin seguimiento. Capturas antiguas regeneradas no añadidas al último commit.
- .env no modificado, mostrado ni empaquetado. Credenciales requeridas existentes; solo uso autorizado en runtime. Usuario compartió contraseña de BD en chat: no se copió a archivos ni se usó desde aquí; recomendada rotación en panel.
- No crear recursos Railway desde esta sesión; usuario configura worker/panel. Propuesta anterior de mayor evaluación no implica aprobación. No consumir JEV training/validation/test/LiveDay adicional; únicamente RSS 10/60 autorizado.

## Comprobación real del worker y JEV · 17-10-2026
- Usuario confirma despliegue del worker. GET /api/worker online true; seis fuentes han completado consultas reales (últimas 200 o 304, errores 0). El monitor ya no muestra aviso de worker sin conexión.
- `python -m scripts.check_rss_execution --analyze`: autenticación 200, encolado 202, 10 trabajos done, **10 HTTP JEV nuevos**, **6,964 s** incluidos encolado/espera; modelo devuelto jev-1.13.0 en los diez resultados. Ningún error, caché o reintento. Solo una etapa necesaria en estos artículos sin candidatos; no se fuerza una segunda llamada vacía.
- **9 review / 1 done / 27 pending**. Revisión por confianza insuficiente de tipo/estado del evento; no se presenta como certeza de riesgo ni como precisión evaluada. RSS no altera exportaciones del ejercicio.
- `python -m scripts.check_rss_execution` sin --analyze verifica de nuevo sin ampliar consumo ni alterar tiempo inicial. Grant persistente queda agotado 10/10; RSS periódico false. Uso del proveedor almacenado por el adaptador en api_calls.usage; no recuperado por estos endpoints, sin estimación de coste inventada.
- Smoke real posterior: /, salud/readiness, catálogo, fuentes, config y assets 200; conserva 40 proveedores y seis fuentes. Chromium público sin mocks: nueve tarjetas al filtrar revisión, siete opciones de fuente (todas + seis), sin errores JS ni overflow a 1440 px, worker activo.
- Evidencia: reports/rss-railway-execution.json, public-deployment-after-rss-jev.json, railway-rss-ui-real.json y capturas railway-rss-*-real.png. Script reproducible nuevo sin valores de credenciales.

## Pendiente / siguiente acción
1. Registrar hito probado y verificar conservación de resultados/cupo tras el autodeploy del script/informes, sin volver a iniciar análisis.
2. Usuario puede revisar Noticias → Noticias reales, filtros Fuente y Estado de análisis. No ejecutar limpieza desde el agente.
3. Consumo adicional requiere nueva autorización concreta. Training inicial y RSS 10/60 agotados; no ejecutar evaluación retenida, test ni LiveDay.
4. Auditoría A01–A20: pendientes evaluación retenida/final, exportación final/LiveDay 14 ≤300 s, audibilidad corregida y dispositivo físico. Este lote de 10 RSS no acredita rendimiento de LiveDay ni aceptación completa.
