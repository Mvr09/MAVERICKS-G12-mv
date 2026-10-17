# Supplier Risk Radar · seguimiento

## Estado actual · 17-10-2026
- Publicado por push autorizado a `origin/main`: **e9e0213af2d8a0bc6a1827e8403cabd6a5a7b395** (hito RSS, aplicación del lote en 8477e5b). Repositorio Mvr09/MAVERICKS-G12-mv; Railway peaceful-harmony / production. No hay acceso directo al panel.
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
1. Hito registrado y publicado: e9e0213. Smoke posterior 20:58:39 UTC confirma SHA, todos los endpoints/assets 200, 40 proveedores, seis fuentes y worker online. Persisten 37 artículos y 10 resultados (9 review/1 done); cupo 10/10 agotado, peticiones siguen en 10. Ningún análisis adicional durante el redeploy. Evidencia local public-deployment-e9e0213.json y rss-persistence-after-redeploy.json.
2. Usuario puede revisar Noticias → Noticias reales, filtros Fuente y Estado de análisis. No ejecutar limpieza desde el agente.
3. Consumo adicional requiere nueva autorización concreta. Training inicial y RSS 10/60 agotados; no ejecutar evaluación retenida, test ni LiveDay.
4. Auditoría A01–A20: pendientes evaluación retenida/final, exportación final/LiveDay 14 ≤300 s, audibilidad corregida y dispositivo físico. Este lote de 10 RSS no acredita rendimiento de LiveDay ni aceptación completa.

## Continuación autorizada: evaluación y ensayo final
- Usuario autoriza **hasta 200 llamadas JEV adicionales** y consultas RSS conforme a límites. Sustituye la propuesta pendiente de 44/264 y la antigua de 83/498. Presupuesto compartido persistente `demo-final-200-20261017`; ventana de 45 min desde primera llamada, sin renovación. Prioridad validación 10 → test 20 → LiveDay 14; después RSS dentro del saldo/cupo diario. Inferencia periódica sigue false.
- Implementados reserva HTTP transaccional y registro de budget por intento; cupo compartido entre grants, etapas y workers, incluidos reintentos. Se exige heartbeat de todos los workers recientes en la misma revisión para impedir que una versión anterior procese trabajos sin este límite.
- Migración 0004 no destructiva: presupuesto, vínculo a intentos/grants, versión de worker y filas privadas de importación para conservar columnas de test. Migración desde base nueva pasa, 20 tablas; no se cambia la política ni las preguntas congeladas.
- Corregidos borradores: usan evidencia validada de la última noticia por fecha de publicación, no una explicación inexistente en assessment ni el último orden de recepción. Resolución manual desactiva sonido de alertas asociadas. Test exporta columnas originales más decisiones, sin etiquetas de evaluación.
- Runner `scripts.final_rehearsal`: fases secuenciales, verificación de hash/manifiesto/congelación, importaciones explícitas, medición hasta Excel recibido, validación de IDs/orden/Y-N/delimitador, métricas privadas y uso API. Artefactos en reports/private y .runtime/final, nunca públicos ni Git.
- Autorización física de audio: solicitados dispositivo/navegador y activar→probar→silenciar→probar; respuesta pendiente. Móvil físico omitido por decisión previa del usuario, no se marca ejecutado.
- Pruebas en curso antes de publicar; consumo de esta autorización todavía 0. Siguiente: terminar regresión/E2E, publicar correcciones y ejecutar ensayo real sin reajustar con resultados retenidos.

- Gate de publicación: **60 pruebas backend/runner pasan**, **13 E2E pasan**, build TS/Vite y paquete permitido pasan; migración desde base nueva y predeploy completo pasan (0004, 20 tablas). Preguntas/política siguen con hashes congelados. Se prepara push autorizado; todavía 0 llamadas nuevas del cupo 200.

## Diagnóstico de la primera ejecución de validación
- Desplegado 8538d60; ambos servicios y todos los workers recientes coinciden en revisión. Iniciado presupuesto a las 21:16:52 UTC, ventana hasta 22:01:52 UTC.
- Validación se detiene correctamente: 8 resultados procesados (7 review, 1 done), 2 error; 14 peticiones HTTP 200 registradas, 186 del nuevo cupo restantes. Un CONTRACT_SCORE y otro PROVIDER_REQUIRES_DIAGNOSIS por bloqueo preventivo. Test/LiveDay no iniciados, exportación bloqueada.
- Consultada documentación primaria TypeSafe Score y API: Score es la suma ponderada de índices por probabilidades. Primera respuesta inválida no conserva diagnóstico numérico, por lo que no se inventa su delta. Se añade captura numérica privada y reconocimiento de diagnóstico por presupuesto, sin reiniciar intentos/cupo ni modificar respuestas.
- Corregido caso sintético independiente: diferencia decimal exactamente 0,03 podía superar la misma tolerancia por coma flotante; usar Decimal mantiene 0,03 sin ampliar umbral. Preguntas/política/rubricas siguen congeladas; no se usan etiquetas retenidas para ajustar.
- Próximo paso: desplegar diagnóstico y hacer un reintento aislado de la fila CONTRACT_SCORE dentro de sus tres intentos por etapa. Si vuelve a ser incoherente, inspeccionar números y detener, no aflojar contrato ni fabricar N.
