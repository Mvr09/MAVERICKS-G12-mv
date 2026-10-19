# Supplier Risk Radar · Helixa Pharmaceuticals

Aplicación en español con React/TypeScript/Vite/Tailwind, FastAPI, SQLAlchemy/Alembic y PostgreSQL. Web y worker comparten imagen; solo la web tiene dominio público. Los datos de Helixa representan una cartera ficticia.

**Estado verificado:** [demo pública](https://mavericks-g12-mv-production.up.railway.app), web/worker compatibles y PostgreSQL persistente, esquema **0008**. Código funcional **a2e962f**; publicación documental posterior y últimas observaciones en [PROGRESS.md](PROGRESS.md). **Default 1.0.0**, candidata explícita **3.4.2 / revisión 1.3.1**, sin promoción. RSS real y análisis manual comprobados; el periódico de pago sigue desactivado. **A06 abierto; A14 físico cerrado** (ordenador/Firefox, una alerta automática QA). A20 conserva su medida histórica:14 artículos LiveDay en7,888295967 s,b4d697b,23 peticiones nuevas / 0 caché; no se presenta como tiempo actual del candidato.

Selección de demo cerrada: usar **3.4.2/revisión1.3.1** explícitamente; mantener **1.0.0** predeterminada. [Comparación pareada, errores y decisión](reports/SELECCION_DEMO_FINAL.md).

Documentación vigente: [comparación y límites](reports/CANDIDATA_OPERATIVA.md), [aceptación A01–A20](reports/ACEPTACION_ACTUAL.md) y [guion de cuatro minutos](docs/09_DEMO_PROCUREMENT.md). Los informes anteriores se conservan como historial, no como evaluaciones nuevas.

## Arranque local con Docker Compose

Requiere Docker Compose, los tres secretos existentes en `.env` y puerto 8000 disponible. No sustituyas `.env` con `.env.example` si ya existe.

```bash
docker compose up --build -d
curl http://localhost:8000/readyz
```

Abrir `http://localhost:8000`. Compose prepara PostgreSQL, ejecuta migraciones y registra las seis fuentes. El worker consulta RSS cada 300 segundos. Las noticias se importan pendientes y no generan llamadas a JEV por defecto. `docker compose stop` conserva el volumen; no usar `down -v` para operar la demo.

Con acceso de presentador, **Importar Excel** permite cargar los archivos explícitos del kit. La imagen excluye los originales; no los incluyas en una publicación de código ni en el contexto Docker. Se procesan en memoria y se persisten filas y hash, sin necesitar el archivo en el contenedor después de importarlo.

## Desarrollo sin Docker

Python 3.12, Node 20.20 y PostgreSQL 16. El lockfile Python contiene versiones completas y el frontend usa `npm ci`.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock
npm --prefix frontend ci
npm --prefix frontend run build
```

Configurar `DATABASE_URL` en el entorno del proceso, conservando el `.env` existente. Ejemplo para una base local propia:

```bash
export DATABASE_URL='postgresql+psycopg://radar:radar_local_only@localhost:5432/radar'
.venv/bin/python -m app.cli config
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En otra terminal con la misma `DATABASE_URL`:

```bash
.venv/bin/python -m app.worker
```

Para desarrollo, cargar explícitamente solo training mediante la interfaz. `import-manifest` es una operación de importación completa para la fase autorizada: lee las cuatro rutas XLSX declaradas en `evidence/input_manifest.json`. Importa todos sus esquemas sin ejecutar inferencia. Una repetición devuelve los lotes existentes. En Railway se usan cargas del presentador, porque el paquete desplegable no contiene `inputs/` ni el manifiesto.

Para trabajar con HMR: `npm --prefix frontend run dev`; el proxy `/api` apunta a FastAPI:8000. Fija `APP_BASE_URL=http://localhost:5173` si vas a usar la sesión desde ese origen. En la demo compilada, API y frontend comparten origen.

## Variables y secretos

No ha sido necesario mapear nombres alternativos. Se usan `TYPESAFE_API_KEY`, `ADMIN_PASSWORD` y `SESSION_SECRET` existentes. `app.cli config` informa únicamente configurada/faltante, nunca valores. `DATABASE_URL` es requerida para persistencia; el valor de ejemplo es solo desarrollo.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Conexión PostgreSQL compartida por web/worker; admite prefijo `postgres://`. |
| `TYPESAFE_API_KEY` | Bearer del backend hacia `https://api.typesafe.ai/v1/systemone`. |
| `ADMIN_PASSWORD` | Acceso compartido de presentador. |
| `SESSION_SECRET` | Firma de cookies; sesiones y revocación en PostgreSQL. |
| `JEV_MODEL` | Versión explícita, por defecto `jev-1.13.0`. |
| `APP_BASE_URL` | Origen exacto autorizado; HTTPS activa cookie Secure. |
| `RSS_ANALYSIS_ENABLED` | Mantener `false`: el análisis periódico de pago no está autorizado para esta demo. |
| `PORT` | La entrada `app.web` escucha en `0.0.0.0:8000`; esta variable no cambia el puerto fijo ni el target 8000 del dominio. |
| `DEMO_FIXTURES_ENABLED` | Solo ensayos identificados de interfaz. No habilita respuestas falsas ni llamadas de pago. |

No existen variables `VITE_*` con credenciales. `.env` queda fuera de Git, Docker, el paquete de despliegue y las rutas públicas. La lectura pública muestra catálogo, resúmenes y decisiones normalizadas; no ofrece etiquetas, Excel originales ni cuerpos de respuesta del proveedor. Las mutaciones requieren sesión y token CSRF; el login limita intentos en PostgreSQL.

## Uso durante la presentación

1. Abrir **Resumen**, seleccionar **Ejercicio** o **Noticias reales** y entrar con **Acceso presentador**.
2. Importar el XLSX. Se reconoce la hoja y se conservan `News_ID` y orden. Revisar el lote en la parte inferior o en Analítica.
3. **Analizar** encola los artículos pendientes sin cupos locales de presupuesto. Los trabajos son persistentes; la interfaz consulta progreso cada tres segundos cuando está visible y al recuperar foco.
4. Abrir proveedor → evidencia literal → factores → productos/materiales/alternativo. `—` significa sin prioridad disponible; no significa ausencia de riesgo. Inventario no informado, no aplicable y cero permanecen distintos.
5. Crear una consulta a proveedor o alternativo desde un incidente sin revisión obligatoria. Editar, guardar, copiar o descargar TXT. No se envía nada. El alternativo debe confirmar disponibilidad; la consulta no constituye un pedido.
6. **Activar sonido**, **Probar alarma**, ajustar volumen y mantener la pestaña activa. **Silenciar** no reconoce ni resuelve incidentes. El contador de la pestaña sigue mostrando alertas sin leer.
7. Cuando todas las filas estén procesadas, **Exportar** descarga `News_ID`, `Is_Risk`, `Urgent`, `Affected_Supplier_IDs`; IDs únicos, ordenados y separados por `; `. Un error bloquea el archivo. Una revisión ya procesada exporta su mejor decisión y conserva su estado de revisión.
8. En **Fuentes**, **Actualizar ahora** encola las seis consultas reales. Cada fuente conserva última consulta, último éxito, HTTP, novedades y error. Las demás continúan si una falla. Una respuesta cacheada de inferencia aparece identificada y no se presenta como consulta nueva.

La prioridad es una regla de atención 0–100, no una probabilidad de quiebra. Se usa el máximo de incidentes activos por proveedor. Los titulares compatibles aportan historia, no suman scores. Las recuperaciones solo cierran un incidente compatible posterior; las asociaciones ambiguas requieren revisión. Una noticia antigua no reabre por sí sola un incidente resuelto.

## Consumo de JEV y fases retenidas

Contrato verificado con la [API oficial](https://docs.typesafe.ai/api), la [lista de modelos](https://docs.typesafe.ai/models) y una llamada autenticada. No se utiliza `/v1/decide`. La versión devuelta se valida, sin sustituciones silenciosas. Se construyen 40 Noul en etapa A; la etapa B agrupa riesgo, urgencia, severidad, evidencia y duración de todos los candidatos. Las cinco columnas de etiquetas se excluyen mediante listas de campos permitidos, también en el payload HTTP probado.

El cupo inicial de tres artículos ya se consumió: N001, N002 y N005; cuatro peticiones HTTP 200, sin reintentos. El informe [jev-local.json](reports/jev-local.json) registra uso y tiempos sin respuestas protegidas. Dos noticias no necesitaron etapa B al no superar candidatos el umbral de revisión. `config/authorization.json` evita reiniciar el cupo al crear otra base.

El usuario desactivó todos los límites locales de presupuesto. `config/authorization.json` fija `budget_limits_enabled=false`: los grants quedan como registros de consumo, sin bloquear por artículos, peticiones, vencimiento o ventana. El antiguo cupo diario RSS tampoco se aplica. En **Fuentes**, **Analizar noticias pendientes con JEV** encola todas las pendientes de una vez. No se requieren variables nuevas en Railway.

La candidata conserva matching3.3 y utiliza preguntas3.4.2/revisión1.3.1. El refinamiento mantiene riesgo y urgencia separados, usa la publicación como referencia temporal y conserva dudas relevantes. Puede repartirse en peticiones independientes con el mismo estado/preguntas, guarda persistente de 36 intentos por generación ydeadline de 60 s. Es un control técnico, no un presupuesto monetario. La caché y el consumo se conservan en PostgreSQL. Se mantienen concurrencia de cuatro solicitudes, reintentos acotados, timeout y manejo de Retry-After/errores del proveedor. Son controles de ejecución; la aplicación no impone presupuesto monetario ni número diario de análisis. El análisis periódico de pago continúa desactivado.

Preguntas y política están congeladas antes de validación: [prompt-freeze.json](reports/prompt-freeze.json). Las métricas retenidas se registran en el informe final. El endpoint de evaluación, exclusivo del presentador, entrega matrices y precision/recall/F1 con denominadores; no devuelve etiquetas ni usa test/LiveDay para ajustar reglas. Un lote incompleto bloquea la evaluación.

## Pruebas reproducibles

Las pruebas de integración solo pueden borrar la base dedicada **radar_test**. `tests/unit` utiliza mocks y casos sintéticos; no importa los originales. La suite raíz y `tests.setup_e2e` tienen fixtures históricos que importan los cuatro Excel: reservarlas para una fase autorizada, no para desarrollar con conjuntos retenidos. No apuntar pruebas a la base de demo o al historial de experimentos.

```bash
.venv/bin/python -m scripts.create_test_database
DATABASE_URL='postgresql+psycopg://radar:radar_local_only@localhost:5432/radar_test' .venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m unittest discover -s reference -p 'test_*.py' -v
npm --prefix frontend run build
# Las pruebas con page.route pueden ejecutarse contra un preview local.
E2E_URL=http://127.0.0.1:4173 SCREENSHOT_PREFIX=local-mock frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts candidate-runtime rss-verification news-continuity buyer-reading origin procurement qa-audio lazy-analytics
```

Playwright usa Chrome en `/opt/google/chrome/chrome` en este equipo. En otro equipo, fija `CHROME_PATH` a tu navegador Chromium instalado. `E2E_URL` permite seleccionar el servidor (por defecto localhost:8000). Para el preview, después del build ejecutar desde `frontend/`: `./node_modules/.bin/vite preview --host 127.0.0.1 --port 4173`. Las pruebas anteriores interceptan API y no requieren importar Excel. Usar prefijos de captura propios.

Recorrido de integración amplio **solo en una fase autorizada**; sus fixtures históricos importan los datasets:

```bash
DATABASE_URL='postgresql+psycopg://radar:radar_local_only@localhost:5432/radar_test' .venv/bin/python -m tests.setup_e2e
DATABASE_URL='postgresql+psycopg://radar:radar_local_only@localhost:5432/radar_test' APP_BASE_URL=http://127.0.0.1:8001 DEMO_FIXTURES_ENABLED=true .venv/bin/uvicorn app.main:app --port 8001
E2E_URL=http://127.0.0.1:8001 E2E_FULL=1 npm --prefix frontend run test:e2e
```

Las pruebas automáticas de audio validan gesto, exclusión de historial, cooldown, una emisión por revisión, mute, foco y estado bloqueado. **No demuestran que un dispositivo haya emitido sonido**. El ensayo auditivo debe registrar dispositivo, navegador y volumen. No se garantiza audio con la pestaña cerrada, el navegador suspendido o el teléfono bloqueado.

Comprobaciones externas autorizadas:

```bash
.venv/bin/python -m scripts.check_rss
.venv/bin/python -m scripts.check_restart
.venv/bin/python -m scripts.smoke http://127.0.0.1:8000
```

`check_rss` consulta realmente seis fuentes; su informe identifica el entorno local. `check_restart` lanza una web auxiliar en 8002, la reinicia y comprueba sesión/rutas/datos. No ejecuta JEV. `check_jev` fue utilizado para el cupo inicial y no debe reiniciarse para obtener presupuesto nuevo.

## Autodeploy del servicio existente

La continuación usa GitHub → Railway sobre el servicio existente y el dominio `https://mavericks-g12-mv-production.up.railway.app`, target port 8000. `railway.json` configura la web por defecto y `python -m app.web` fija `0.0.0.0:8000`. El `.env` local no se transfiere: variables, PostgreSQL y dominio se revisan en el panel por el usuario. El push ha sido autorizado; no amplía el presupuesto de JEV. [Pasos de panel y diagnóstico](docs/09_AUTODEPLOY_EXISTENTE.md).

## Railway: artefactos y recuperación

Repositorio `Mvr09/MAVERICKS-G12-mv`, rama `main`, autodeploy existente. Web yworker se comprueban por HTTPS/heartbeat; la persistencia usa PostgreSQL. No se dispone de acceso administrativo al panel y no se han creado recursos. Versión funcional verificada **a2e962f**, con las observaciones finales enlazadas en PROGRESS.md. No se necesita crear otro proyecto. Los originales ya seguidos en el repositorio se excluyen de la imagen mediante copias explícitas y del paquete permitido.

```bash
.venv/bin/python -m scripts.package_deploy
```

Esto genera `.runtime/deploy/` y `.runtime/supplier-risk-radar-deploy.tar.gz` con una lista permitida, sin `.git`, secretos, originales, etiquetas o informes privados. El Dockerfile copia explícitamente código y frontend compilado; ejecuta con UID 10001. Validar `docker build -t supplier-risk-radar:demo .runtime/deploy` en un equipo con Docker o en el build autorizado de Railway; este equipo no dispone de daemon Docker.

Para reproducir la configuración en un entorno autorizado (el actual ya está desplegado):

1. Crear/seleccionar proyecto y entorno aprobados; añadir PostgreSQL con volumen persistente.
2. Crear web y worker desde el mismo paquete y Dockerfile. Seleccionar `railway.web.json` para web y `railway.worker.json` para worker. Desactivar suspensión del worker durante la demo.
3. Vincular `DATABASE_URL` al PostgreSQL privado en ambos servicios; transferir las tres credenciales existentes usando el gestor de variables, sin imprimirlas ni regenerarlas. Fijar `JEV_MODEL=jev-1.13.0`. Solo web ejecuta `python -m app.predeploy` (migración y seed secuenciales); worker espera esquema.
4. Generar dominio HTTPS únicamente para web; fijar `APP_BASE_URL` al dominio exacto. Confirmar `/readyz`, cookie Secure y rutas profundas.
5. Cargar Excel por sesión de presentador. La base conserva el resultado tras redeploy; el contenedor no necesita los originales. Aplicar únicamente los grants de consumo aprobados.
6. Consultar las seis fuentes desde Railway y registrar evidencia nueva (al menos cuatro saludables). Ejecutar análisis RSS autorizado y mostrar exposición potencial de cartera simulada.
7. Protocolo actual:training y sintéticos para desarrollo; validación inspeccionada es retrospectiva. Test restante conserva su fase final; LiveDay ya se ejecutó y no se reutiliza para ajustar. Los comandos siguientes se reservan para un ensayo final nuevo autorizado, si una adopción de modelo requiere renovar A20; no ejecutarlos para repetir la medición histórica:

```bash
.venv/bin/python -m scripts.smoke URL_HTTPS_REAL
.venv/bin/python -m scripts.measure_batch URL_HTTPS_REAL ID_LOTE_LIVEDAY
```

8. Reiniciar web/worker y verificar persistencia y recuperación de leases. Ensayar audio y uso móvil real. Actualizar auditoría antes de declarar aceptación completa.

Las migraciones inversas destructivas están bloqueadas deliberadamente. No se borran datos para recuperar un worker: un lease vencido se reclama transaccionalmente, con heartbeat e intentos acotados; al agotar intentos queda error visible. Una respuesta de JEV inválida permanece error y bloquea exportación. No editar respuestas de test/LiveDay a mano.

## Operación de la demo

[Guía paso a paso](docs/10_OPERACION_DEMO.md): Materiales, worker, progreso RSS, análisis manual JEV sin límites locales de presupuesto y con registro persistente de consumo y limpieza mediante checkboxes de lotes/fuentes, catálogo con dependencias y reanálisis con historial. RSS admite contraste auxiliar con tres evaluaciones JEV; no retira revisiones automáticamente. El análisis periódico de pago permanece desactivado. La web usa `python -m app.predeploy` para migrar e inicializar las seis fuentes y cupos de forma idempotente.
