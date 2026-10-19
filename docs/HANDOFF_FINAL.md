# Entrega al equipo · 19 de octubre de 2026

## Versión y perfil habitual

El commit de implementación se identifica en `git log --oneline -- app/final_model.py`; la verificación posterior se registra en `PROGRESS.md`. Publicación por `main` y autodeploy existente, web y worker con la misma imagen. URL: https://mavericks-g12-mv-production.up.railway.app.

Se promueve por decisión de producto el perfil **3.4.2 / revisión 1.3.1** de la campaña `6c4ca3ce-8d4b-44ee-bbd9-6209e7dce3c7`, conservando su identificador histórico interno `radar-1.0.0-candidate`. El manifiesto completo está en `config/final_profile.json`: matching `link-3.3.0`, recuperación `link-3.0.0-dev`, preguntas `decision-3.4.2`, riesgo `risk-focus-1.2.0`, revisión `review-1.3.1`, soporte `decision-support-1.0.0`, hechos `decision-facts-1.0.0`, exclusión `relational-exclusion-1.0.0`, duración `duration-1.1.0`, transporte `fanout-1.0.0`, política empresarial `1.0.0`, JEV `jev-1.13.0`.

`app/profiles.py:DEFAULT_PROFILE` y `frontend/src/AnalysisProfile.tsx:DEFAULT_ANALYSIS_PROFILE` fijan el default; API, Excel, RSS individual y por lote lo reutilizan. Las opciones avanzadas conservan `1.0.0`. Rollback global: cambiar esas dos constantes a `LEGACY_PROFILE` / `"1.0.0"`, ejecutar las pruebas y desplegar web/worker juntos. **No cambiar el manifiesto final ni reasignar trabajos existentes.** Los trabajos antiguos sin perfil conservan el fallback 1.0.0; los nuevos guardan una instantánea completa y el worker rechaza discrepancias. Las claves de caché de nuevas ejecuciones incluyen esa instantánea. La promoción no reanaliza históricos, modifica decisiones humanas ni reproduce alertas.

## Interfaz y operaciones

El sistema compartido está en `frontend/src/style.css`: `.workspace`, `.main`, tarjetas, grids según espacio disponible, filtros, tablas con desplazamiento local y consultas de contenedor. `OperationFeedback.tsx` aporta carga con espacio reservado, botones con bloqueo contra doble envío y error local, y descarga preparada tras una respuesta HTTP válida. `api.ts` limita peticiones a 30 segundos y no reintenta mutaciones automáticamente.

La importación informa de validación; los análisis muestran cola, procesamiento, conteos reales y errores parciales. `PendingAnalysis.tsx` persiste el identificador de solicitud y consulta primero el manifiesto al recuperar un envío dudoso; no repite a ciegas. El seguimiento se detiene con error visible y permite recuperarlo. Revisiones, acciones y borradores conservan sus componentes y persistencia; Modelo y las herramientas administrativas se cargan de forma diferida. Los errores de guardado mantienen el texto. QA/audio/preparación demo siguen recogidos. No se envían comunicaciones.

## Modelo y procedencia

La página normal muestra exclusivamente el perfil final; el histórico y comparador se conservan para presentadores en `/administracion/modelo`, además de las API privadas de campañas/exportación. `/api/model/final` solo agrega resultados persistidos del ID, hash y componentes exactos; no invoca JEV ni expone etiquetas individuales. El filtro training/validation retrospectiva/total etiquetado agrega TP/FP/FN antes de recalcular. Las predicciones revisadas cuentan; las decisiones humanas no las sustituyen. Test/LiveDay no tienen precisión evaluada sin referencias.

Campaña original: 148 análisis nuevos, 74 por perfil; el final utilizó 265 peticiones. En los 40 etiquetados del final: riesgo TP19/FP0/FN0/TN21; urgencia TP7/FP2/FN0/TN31; asociaciones TP32/FP5/FN0, conjuntos exactos 37/40. Automáticas 19/40, con 0/19 errores; 21 requieren revisión. Training y validation conocidos **no son validación independiente** ni garantizan calidad en RSS.

La duración individual se calcula como `completed_at - started_at`, no como duración de campaña paralela / filas. La campaña local importada tiene 74 análisis finales con inferencia nueva: media 2,14067257 s, mediana 2,20809 s y p95 3,514059 s; cola aparte. La infraestructura y periodo originales se muestran en la página. Las nuevas marcas del worker separan mediciones Railway, caché e inferencia nueva; no se mezclan con la muestra local. El tiempo conserva el inicio del primer intento si el trabajo se reintenta.

## Simulador

`frontend/src/simulator.ts` valida enteros no negativos y valores finitos. Tokens estimados = X × Y; coste = X × Y / 1.000.000 × tasa. La tasa histórica editable por defecto es **0,03941248835 $ por millón de tokens**, derivada de la referencia del usuario del 19/10/2026: 2,6045 $ / 66.083.115 tokens × 1.000.000, asumiendo igual ámbito y periodo. No es tarifa oficial, no se presume divisa ni se separan precios de entrada/salida/caché.

Y parte de la media de entrada + salida reportadas en **todas** las llamadas por noticia: 31.333,2568 tokens en esta campaña. Es una aproximación, no certificación de tokens facturables; la API no informa del tratamiento de caché del proveedor. Tiempo secuencial sin cola = X × media individual local; variar Y cambia coste, no simula una latencia calibrada. No se divide por workers teóricos. Los supuestos están en `config/final_profile.json`; los escenarios se conservan solo en sesión del navegador y no crean análisis ni alteran métricas. Importes positivos pequeños nunca se presentan como gratis.

## Desarrollo y comprobación

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock
npm --prefix frontend ci
# Configurar .env local, sin subirlo; PostgreSQL disponible.
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
npm --prefix frontend run build
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# Otro proceso con el mismo entorno:
.venv/bin/python -m app.worker
# Solo sobre una base de pruebas aislada:
DATABASE_URL=postgresql+psycopg://USUARIO@localhost:5432/radar_test .venv/bin/python -m pytest tests/unit -q
E2E_URL=http://127.0.0.1:8000 npm --prefix frontend run test:e2e
.venv/bin/python -m scripts.package_deploy
```

La imagen compila frontend y sirve todo desde FastAPI, puerto 8000. Predeploy: `alembic upgrade head && python -m app.cli seed`. `.env` local no configura Railway; web y worker necesitan las variables del servicio y PostgreSQL. El empaquetador usa lista permitida y comprobación de secretos. No se cambia facturación ni recursos externos.

## Límites y continuación

- **A06 abierto**: separar errores del motor con datos suficientes (incluido el diagnóstico S024) de la provincia desconocida de S003/Taizhou. No completar ubicaciones, plantas o rutas sin procedencia. La promoción autorizada no resuelve este criterio.
- Cinco asociaciones adicionales y dos urgencias falsas en los 40 etiquetados del final; no confundir recall perfecto en esta muestra conocida con ausencia de omisiones futuras. Mantener revisión humana y soporte verificable.
- A14 conserva evidencia física de ordenador/Firefox: activación, silencio y una alerta QA automática única. Las pruebas de navegador no acreditan nueva audibilidad física.
- A20 conserva su medición histórica y alcance; la campaña comparativa local y las dos comprobaciones de cierre no renuevan el protocolo de 14 filas en Railway. No se repite LiveDay para este cierre.
- RSS periódico de pago permanece desactivado. Análisis explícitos de presentador y contadores de consumo se conservan. No se publica dataset ni answer key.
