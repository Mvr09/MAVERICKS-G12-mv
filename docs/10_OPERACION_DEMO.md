# Preparar y operar la demo

## Datos persistentes

La aplicación publicada guarda catálogo, noticias, resultados y trabajos en PostgreSQL de Railway. Recargar el navegador o desplegar de nuevo no los borra. El navegador conserva preferencias de la pestaña y la cookie de sesión; no es la base del catálogo.

## Materiales

Abrir **Materiales** en el menú: catálogo completo con búsqueda por nombre, ID, producto o proveedor y filtro por categoría. **Ver especificaciones** abre los datos disponibles del Excel, productos y enlaces al proveedor principal y alternativo. No se inventan especificaciones técnicas ausentes ni disponibilidad del alternativo.

## Worker separado

En el proyecto Railway, comprobar si existe un servicio cuyo comando sea `python -m app.worker`. Si no existe, el usuario puede crear un servicio desde el mismo GitHub `Mvr09/MAVERICKS-G12-mv`, rama `main`, y llamarlo `worker`. Su coste de infraestructura depende de la cuenta Railway.

- Raíz `/`, Dockerfile de la raíz, configuración `/railway.worker.json`.
- Comando `python -m app.worker`; sin predeploy, healthcheck HTTP ni dominio.
- `DATABASE_URL`: referencia al mismo PostgreSQL que web.
- Configurar `TYPESAFE_API_KEY`, `ADMIN_PASSWORD` y `SESSION_SECRET` existentes; no copiarlos al chat, frontend o Git.
- `JEV_MODEL=jev-1.13.0`, `RSS_ANALYSIS_ENABLED=false`, `DEMO_FIXTURES_ENABLED=false`.
- Web ejecuta `python -m app.predeploy`: migra a 0005 e inicializa seis fuentes y cupos sin reiniciar consumo. El worker espera el esquema antes de procesar.
- La pantalla **Fuentes** muestra «Procesamiento sin conexión» si no recibe heartbeat durante 30 s. Esto no afirma que el servicio no exista: también puede estar caído o apuntar a otra base.

**Actualizar ahora** registra las fuentes si faltan y encola inmediatamente una consulta por fuente. Un clic repetido reutiliza consultas pendientes. El worker reclama trabajos transaccionalmente y comienza a procesarlos; la consulta periódica gratuita se mantiene cada cinco minutos. La web muestra solicitudes, cola, consultas en curso, resultados, errores y últimas incorporaciones reales. Sin worker no se simula actividad ni se inventan noticias.

Noticias muestra filtros por **Fuente**, **Lote de origen**, estado, fechas, evento y proveedores identificados. El selector superior separa Ejercicio de Noticias reales. Entrar desde el stream RSS selecciona el contexto de noticias reales.

## Autorización vigente: JEV manual sin cupo

El usuario autoriza cupo ilimitado para probar manualmente. El presupuesto `manual-unlimited-20261017` no tiene límite de peticiones ni vencimiento; hay autorizaciones para training, validation, test, LiveDay y RSS sin tope local de artículos. El predeploy las crea una sola vez y conserva los contadores anteriores. No hace falta editar variables ni pegar claves de nuevo.

En **Ingesta**, seleccionar el lote y pulsar **Analizar**. Los resultados existentes se conservan y se reutiliza la caché; no se recalculan automáticamente ni se modifican respuestas retenidas para ajustar el modelo. En **Fuentes**, pulsar **Actualizar ahora** para consultar RSS y **Analizar hasta 10 noticias con JEV** para analizar las pendientes. Repetir el análisis manual para otros grupos pendientes.

«Sin límite» se refiere al cupo de consumo autorizado de la aplicación: no cambia el saldo, la facturación ni los límites de TypeSafe. Siguen vigentes la concurrencia máxima, tres intentos por etapa, diagnóstico ante errores de contrato/autenticación y el cupo técnico RSS de **100 artículos por día UTC**. No se activa inferencia periódica de pago. `GET /api/admin/budgets` muestra el presupuesto ilimitado con límites nulos y el contador real de llamadas; los presupuestos históricos permanecen visibles.

## Historial: primer lote JEV autorizado

Autorización del usuario del 17-10-2026: **hasta 10 noticias RSS, máximo 60 peticiones HTTP, reintentos incluidos**. Grant `rss-demo-20261017-10`, con vencimiento de seguridad 19-10-2026 00:00 UTC. No se añaden autorizaciones de training, validación, test ni LiveDay.

Con worker conectado y noticias recibidas, el presentador puede pulsar **Analizar hasta 10 noticias con JEV** en Fuentes. El cupo persistente limita la selección a lo disponible y la API registra intentos por artículo y etapa (máximo tres por etapa, seis por artículo). El presupuesto diario del kit también se aplica. Repetir clic, reiniciar o desplegar no restablece el cupo. Las respuestas cacheadas se distinguen de nuevas peticiones. Fallos de autenticación/contrato bloquean peticiones posteriores del mismo grant hasta diagnóstico; las que ya estuvieran en vuelo pueden terminar.

`RSS_ANALYSIS_ENABLED=false` mantiene desactivada la inferencia periódica; no impide ejecutar este lote manual con grant explícito. Los artículos no incluidos quedan pendientes. El límite inicial de tres artículos de entrenamiento permanece agotado.

## Limpiar para la demo

**Preparar demo** abre una vista previa y no borra al abrirse. El presentador revisa cantidades, escribe `LIMPIAR DEMO` y pulsa **Eliminar Entrenamiento y LiveDay**.

- Elimina esos lotes, sus noticias y resultados, trabajos y elementos asociados exclusivamente a ellos.
- Conserva proveedores, materiales, RSS, validación, test y sus resultados, sesiones y fuentes.
- Conserva el consumo y registro de llamadas JEV. La limpieza no concede presupuesto ni permite reusar una autorización agotada.
- Si hay análisis del alcance en curso, datos cambiados desde la vista previa o incidentes compartidos con lotes que deben conservarse, rechaza la operación sin borrado parcial.
- Después se pueden volver a importar los Excel para la demo; inferencia adicional requiere autorización específica.

La implementación no ejecuta esta limpieza automáticamente ni el agente la ejecuta como parte del despliegue.

## Audio

**Activar sonido** requiere un gesto. **Silenciar** bloquea tanto avisos automáticos como **Probar alarma**; para volver a probar, activar de nuevo. El aviso visual se conserva. La prueba del navegador no certifica audibilidad en un dispositivo físico.

## Historial: evaluación y ensayo final de 200 llamadas

El usuario autoriza hasta 200 llamadas JEV adicionales compartidas entre validación, test, LiveDay y RSS. El presupuesto se reserva transaccionalmente antes de cada intento HTTP, incluye reintentos, persiste al desplegar y cierra su ventana 45 minutos después de la primera llamada. Nunca se renueva automáticamente. El cupo anterior de training y RSS permanece agotado.

Se ejecuta primero validación (10), después test (20) y LiveDay (14), con preguntas/política ya congeladas. El ensayo mide desde la solicitud de análisis hasta recibir el Excel exportable; no extrapola tiempos de RSS. La exportación de test conserva las columnas de entrada y añade las decisiones calculadas, sin copiar etiquetas de evaluación.

Comprobación reproducible desde el workspace autorizado:

```bash
.venv/bin/python -m scripts.final_rehearsal --start --rss-after
```

Sin `--start`, el script solo revisa estado. `--rss-after` procesa noticias RSS pendientes al terminar las tres fases, respetando el saldo compartido, la ventana y el cupo diario. No ejecutarlo para crear una nueva autorización. Los resultados completos y métricas están en `reports/private/final-rehearsal.json`; Excel en `.runtime/final/`. Estos directorios no se publican. `GET /api/admin/budgets` y `/api/batches/{id}/execution` requieren presentador y permiten consultar límites, intentos, modelo y uso numérico reportado por la API.
