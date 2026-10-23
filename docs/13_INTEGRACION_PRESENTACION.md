# Aplicación dentro de la presentación · 23/10/2026

## Alcance y publicación

- Aplicación: `https://mavericks-g12-mv-production.up.railway.app/?context=exercise`.
- Único origen externo autorizado: `https://helixa-signal-to-action.jvaswiss-9277.chatgpt.site`.
- Backend recibido: `86edd28`, rama `main`, remoto GitHub existente y autodeploy Railway. Presentación independiente: proyecto `appgprj_6ad8f85204508191992edcdf7eba49fb`, origen de código `616b0ec`, versión pública inicial9.
- Primero publicar Railway y comprobar sus cabeceras; después activar `EMBED_ENABLED = true` en `dist/app.js` de la presentación y publicar esa versión. No basta con actualizar el repositorio de Railway.
- No cambian modelo, métricas, fórmulas, grants, datos históricos ni análisis RSS periódico de pago. Las pruebas de integración no requieren inferencias JEV/Claude ni envíos externos.

## Cabeceras y permisos

`app/embedding.py` y el middleware existente de `app/main.py` aplican a HTML y redirecciones de navegación:

```text
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self' https://helixa-signal-to-action.jvaswiss-9277.chatgpt.site; base-uri 'self'; form-action 'self'
```

No se emite `X-Frame-Options` en esas respuestas. API/JSON, recursos privados y sus errores conservan `DENY` y `frame-ancestors 'none'`; esto no impide el fetch del iframe, que sigue siendo del mismo origen que la API. No se añade CORS ni acceso desde JavaScript de Sites a la API. Las rutas profundas sirven el mismo frontend y la misma política. La aceptación es abriendo el Site directamente; un marco exterior adicional no autorizado puede bloquear la cadena de ancestros intencionadamente.

## Sesión y cookies

En HTTPS, `radar_session` conserva firma/expiración de8h, `HttpOnly`, `Secure`, `Path=/`, sin Domain, con `SameSite=None` para acceso consentido entre sitios. Cuando el propio frontend está embebido añade `X-Radar-Embed: 1` a sus peticiones de API; el login también emite `radar_embed_session` con esos atributos y `Partitioned` (CHIPS). El atributo se serializa explícitamente porque el runtime Python3.12 no lo soporta en su API de cookies. El encabezado no concede permisos.

La identificación acepta una sesión firmada vigente y el cierre revoca el registro y elimina ambas cookies, incluida la particionada. En desarrollo HTTP se mantiene Lax y no se crea una cookie None insegura. No se transmite una sesión por URL, almacenamiento JS ni postMessage.

Tras login el frontend consulta de nuevo `/api/session`: solo muestra presentador si la cookie realmente persiste. `Origin` sigue validándose contra el origen de Railway y las mutaciones requieren el CSRF existente. El origen Sites no pasa a ser un origen de API autorizado.

Si el navegador no permite la sesión, el aviso integrado ofrece un enlace explícito a una ventana independiente. También puede solicitar `document.requestStorageAccess()` directamente en un gesto del usuario: primero visitar/autenticarse en la ventana de Railway y después conceder acceso si el navegador lo requiere. Una denegación conserva una salida útil; no se pide desactivar protección de seguimiento. Las sesiones particionadas pueden ser distintas de la ventana independiente.

## Contrato de mensajes v1

Únicamente confirma disponibilidad/navegación; nunca autenticación ni contenido de negocio. El padre verifica origen exacto, `event.source === iframe.contentWindow`, tipo, versión, ID de correlación y campos. La app verifica origen exacto y `event.source === window.parent`. Todos los envíos usan targetOrigin exacto; no `*`.

Padre → app:

```json
{"type":"helixa:hello","version":1,"requestId":"UUID-aleatorio-de-correlacion"}
```

App → padre, tras catálogo/datos principales, configuración y consulta de sesión inicial:

```json
{"type":"radar:ready","version":1,"requestId":"mismo-UUID","path":"/noticias","context":"exercise"}
```

`requestId` es un identificador público de correlación, no una credencial. La app no envía contraseña, CSRF, cookies, resultados ni claves. `context` admite exercise/rss; `path` es solo pathname sin query. Una navegación interior vuelve a emitir ready con el mismo ID. La presentación valida longitud y caracteres del path antes de mostrarlo. No lee DOM ni URL internos entre orígenes.

El padre pregunta periódicamente durante la carga y espera hasta20s. `iframe.load` solo da pie a preguntar, nunca muestra éxito por sí solo. En timeout ofrece Reintentar/App real, sin afirmar fallo de autenticación. Recibir un ready significa aplicación inicializada; no significa que el usuario sea presentador.

## Cambios concretos de Sites

- Activar `const EMBED_ENABLED = true` después del backend; conservar APP_URL y rutas reales con `?context=exercise`.
- Implementación del handshake anterior en `dist/app.js`; comprobación estricta de source/origin/version/requestId y estado de carga real.
- Iframe: `allow="autoplay; fullscreen; clipboard-write"` y sandbox `allow-scripts allow-same-origin allow-forms allow-downloads allow-popups allow-popups-to-escape-sandbox allow-storage-access-by-user-activation`.
- `allow=autoplay` no activa sonido: el usuario pulsa Activar sonido dentro de Railway; la elegibilidad/cooldown/QA existentes siguen intactos.
- Estado de carga fuera del viewport para no tapar controles; enlace App real y reintento visibles también al ampliar. Botón de retorno restaura la presentación sin recargar el iframe.
- No interceptar Escape dentro de la app para forzar retorno: puede ser necesario para cerrar sus diálogos. El retorno explícito está en la barra exterior.

## Pruebas reproducibles

```bash
npm --prefix frontend run build
.venv/bin/python -m pytest tests/unit/test_embedding.py -q
# Otro proceso: backend de contrato con autenticación/CSP reales y datos MOCK, sin PG/IA.
PYTHONPATH=. .venv/bin/python tests/embed_server.py
FIREFOX_PATH=/ruta/a/firefox npm --prefix frontend run test:e2e -- --config=playwright.embed.config.ts --workers=2
```

El servidor de pruebas solo escucha127.0.0.1:4188; no se empaqueta en Docker ni se despliega. Los tests usan orígenes HTTPS interceptados localmente y el middleware/autenticación reales, con catálogo y fallos explícitamente MOCK. Verifican cookies, login/recarga/logout, CSRF, rechazo del padre no autorizado, carga demorada y recuperación de cookie bloqueada. No sustituyen el recorrido real en la presentación publicada.

La verificación real debe registrar SHA web/worker, valores de CSP/XFO y atributos de cookies **sin valores**, navegadores, rutas, borrador/acción de ejercicio, exportación y ruta QA. La ejecución técnica del audio no acredita audibilidad física: conserva la evidencia histórica A14 y solicita ensayo humano solo si se necesita acreditar audio dentro del iframe. A20 y A06 mantienen su alcance anterior.
