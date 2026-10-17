# Autodeploy del servicio existente

URL aportada: https://mavericks-g12-mv-production.up.railway.app

GitHub registra el entorno `peaceful-harmony / production` y el check `peaceful-harmony - MAVERICKS-G12-mv`. No hay acceso directo al panel Railway desde esta sesión. El `.env` local **no configura** las variables remotas.

El repositorio incluye `railway.json` como configuración web predeterminada, equivalente a `railway.web.json`. Railway detecta por defecto este nombre ([referencia oficial](https://docs.railway.com/config-as-code/reference)). El Dockerfile compila React con `npm ci` y sirve sus assets desde FastAPI. El entrypoint `python -m app.web` escucha explícitamente en **0.0.0.0:8000**, independientemente de un PORT diferente heredado del panel.

## Comprobar en el panel si falla el autodeploy

1. Abrir el servicio web `MAVERICKS-G12-mv` del proyecto existente, entorno `production`.
2. **Settings → Source**: repositorio `Mvr09/MAVERICKS-G12-mv`, rama de autodeploy confirmada, raíz del repositorio `/`. No seleccionar `frontend/` como raíz.
3. **Settings → Build**: Dockerfile `Dockerfile` en la raíz. **Config File**: `/railway.json` (o `/railway.web.json`, equivalente). Si se había seleccionado otro archivo, corregirlo.
4. **Settings → Deploy**: Start Command `python -m app.web`; predeploy `alembic upgrade head` seguido de `python -m app.cli seed`; healthcheck `/readyz`. Estos campos ya están en railway.json. No poner migraciones en el worker.
5. **Settings → Networking → Public Networking**: conservar el dominio indicado y **Target Port 8000**, asociado al servicio web.
6. **Variables** de web: establecer `PORT=8000`, `APP_BASE_URL=https://mavericks-g12-mv-production.up.railway.app`, `JEV_MODEL=jev-1.13.0`, `RSS_ANALYSIS_ENABLED=false` y `DEMO_FIXTURES_ENABLED=false`.
7. Añadir `DATABASE_URL` con **Add Reference** al servicio PostgreSQL existente. Si se llama `Postgres`, la referencia habitual es `${{Postgres.DATABASE_URL}}`; elegir el nombre real desde el selector. No usar localhost ni copiar la URL de desarrollo. Si no existe PostgreSQL, esa dependencia debe provisionarla el usuario en el panel.
8. Configurar `TYPESAFE_API_KEY`, `ADMIN_PASSWORD` y `SESSION_SECRET` con los valores existentes, directamente en el gestor de variables de Railway. No pegarlos en el chat ni en Git. Conservar esos nombres; no crear variables VITE_* para secretos.
9. Aplicar cambios y redeploy del último commit publicado. Si hay worker existente, seleccionar `/railway.worker.json`, comando `python -m app.worker`, la misma DATABASE_URL y `RSS_ANALYSIS_ENABLED=false`; no darle dominio público.

Una base remota nueva empieza sin catálogo: seed registra las seis fuentes y conserva el cupo JEV inicial agotado. Para ver 40 proveedores, entrar como presentador y cargar el Excel de entrenamiento desde la UI. Esto no ejecuta inferencia; no subir los originales como assets públicos.

## Logs necesarios para diagnosticar un fallo

- Si falla **Build**, copiar el bloque desde el primer error de npm/Docker/pip y las 30 líneas que lo preceden, junto con el SHA de la ejecución.
- Si pasa Build y falla **Deploy / Pre-deploy**, copiar las últimas 80 líneas: salida de Alembic, seed, arranque de Uvicorn y healthcheck. Si hubiera credenciales o una URL de PostgreSQL con contraseña, ocultarlas antes de compartir.
- Un 404 con `Application not found` procede del enrutamiento de Railway y por sí solo no identifica el error del proceso. Se necesita el estado del deployment y su log para distinguir build, variables, base de datos o dominio.

Comprobación externa reproducible, sin llamadas de pago:

```bash
.venv/bin/python -m scripts.check_public_deployment --expected-commit SHA_PUBLICADO
```

El script consulta `/`, `/healthz`, `/readyz`, catálogo, fuentes, configuración y assets encontrados en HTML; guarda HTTP, hora y versión observada. No considera el push como prueba de despliegue correcto. No inicia análisis RSS ni cambia los grants de consumo.

## Diagnóstico confirmado por el log recibido

El log del usuario muestra `connection refused` contra `localhost:5432` (IPv4 e IPv6). El proceso web intenta alcanzar una base dentro de su propio contenedor; esa dirección no conecta con un servicio PostgreSQL independiente.

En el panel del proyecto `peaceful-harmony`, entorno `production`:

1. Localizar el servicio PostgreSQL del mismo entorno. Si no existe, la dependencia pendiente es añadir un servicio PostgreSQL desde **New → Database → PostgreSQL**, operación que realiza el usuario en su cuenta.
2. Abrir **MAVERICKS-G12-mv → Variables** y editar `DATABASE_URL`.
3. Usar el selector de referencias para elegir **servicio PostgreSQL → DATABASE_URL**. Si el servicio se llama `Postgres`, el valor de referencia es `${{Postgres.DATABASE_URL}}`. Si tiene otro nombre, usar el nombre real. No copiar la URL local ni pegar credenciales en el chat. [Referencias entre servicios](https://docs.railway.com/variables#reference-variables).
4. Conservar `APP_BASE_URL=https://mavericks-g12-mv-production.up.railway.app`, `PORT=8000` y `RSS_ANALYSIS_ENABLED=false`.
5. En **Settings → Deploy**, comprobar **Pre-deploy Command**: `alembic upgrade head && python -m app.cli seed`, y **Healthcheck Path**: `/readyz`. Así una ejecución sin base o sin esquema no se valida solo porque `/` sirva HTML.
6. Aplicar los cambios y desplegar de nuevo. Si después aparece `DATABASE_SCHEMA_UNAVAILABLE`, revisar la salida de Alembic; no borrar la base ni marcar migraciones como aplicadas manualmente.

Corrección de código complementaria: en Railway se rechazan destinos loopback antes de conectar; fallos de conexión/esquema devuelven JSON 503 sin SQL, credenciales ni tracebacks repetidos. La UI limita los reintentos automáticos a uno cada 30 segundos durante un fallo, manteniendo consulta inmediata al recuperar foco. Esto reduce el volumen de logs, pero no crea ni configura PostgreSQL remoto.
