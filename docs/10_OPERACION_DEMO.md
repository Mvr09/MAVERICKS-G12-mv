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

En **Ingesta**, seleccionar el lote y pulsar **Analizar**. Los resultados existentes se conservan y se reutiliza la caché; no se recalculan automáticamente ni se modifican respuestas retenidas para ajustar el modelo. En **Fuentes**, pulsar **Actualizar ahora** para consultar RSS y **Analizar noticias pendientes con JEV** para encolar todas las pendientes de una vez.

El usuario ha desactivado todos los controles locales de presupuesto (`budget_limits_enabled=false`): no hay tope diario RSS, vencimientos, ventanas, número máximo de llamadas ni cupo por lote. Los presupuestos/grants antiguos se conservan como historial, sin bloquear solicitudes. El botón encola todas las pendientes; un límite explícito en la API es solo una selección voluntaria de artículos. Siguen vigentes la concurrencia máxima, tres intentos por etapa y diagnóstico ante errores de contrato/autenticación. No se activa inferencia periódica de pago. `GET /api/admin/budgets` muestra el presupuesto ilimitado con límites nulos y el contador real de llamadas; los presupuestos históricos permanecen visibles.

## Historial: primer lote JEV autorizado

Autorización del usuario del 17-10-2026: **hasta 10 noticias RSS, máximo 60 peticiones HTTP, reintentos incluidos**. Grant `rss-demo-20261017-10`, con vencimiento de seguridad 19-10-2026 00:00 UTC. No se añaden autorizaciones de training, validación, test ni LiveDay.

Con worker conectado y noticias recibidas, el presentador puede pulsar **Analizar hasta 10 noticias con JEV** en Fuentes. El cupo persistente limita la selección a lo disponible y la API registra intentos por artículo y etapa (máximo tres por etapa, seis por artículo). El presupuesto diario del kit también se aplica. Repetir clic, reiniciar o desplegar no restablece el cupo. Las respuestas cacheadas se distinguen de nuevas peticiones. Fallos de autenticación/contrato bloquean peticiones posteriores del mismo grant hasta diagnóstico; las que ya estuvieran en vuelo pueden terminar.

`RSS_ANALYSIS_ENABLED=false` mantiene desactivada la inferencia periódica; no impide ejecutar este lote manual con grant explícito. Los artículos no incluidos quedan pendientes. El límite inicial de tres artículos de entrenamiento permanece agotado.

## Preparar demo: seleccionar, borrar o reanalizar

1. Entrar como presentador y abrir **Preparar demo**.
2. Marcar los lotes Excel o fuentes RSS deseados. No hay ninguna opción marcada por defecto. **Seleccionar todo** incluye el catálogo; para conservarlo, desmarcarlo.
3. Elegir **Borrar datos seleccionados** o **Volver a ejecutar el análisis**.
4. Pulsar **Revisar alcance**. La vista muestra noticias, análisis, incidentes, alertas y borradores relacionados; al reanalizar indica el máximo de peticiones nuevas.
5. Escribir **LIMPIAR DEMO** para borrar, o **REANALIZAR** para ejecutar consultas nuevas, y confirmar. Cambiar la selección invalida la vista previa y exige revisarla de nuevo.

El borrado de un lote permite cargar de nuevo su Excel. El borrado de RSS conserva la configuración de la fuente y limpia sus cabeceras condicionales: **Actualizar ahora** podrá consultar el feed completo que el proveedor siga ofreciendo. Para borrar noticias de Excel se selecciona el lote completo, evitando una importación parcial ambigua. Una noticia individual puede reanalizarse desde su ficha.

El catálogo solo puede borrarse si también se seleccionan todas las noticias que dependen de él. Las opciones no seleccionadas permanecen. En incidentes compartidos se retiran solo las evidencias seleccionadas y se recalcula el estado con las restantes; sus alertas y borradores anteriores también dependen de esa evidencia y se incluyen expresamente en el alcance. Un aviso visual regenerado por esta operación no reproduce sonido.

Un trabajo en ejecución bloquea la operación. Una vista previa caduca a los 15 minutos o al cambiar los datos; no se ejecuta un borrado parcial. No se borran ni se devuelven consumos: ApiCall, caché, contadores y registro diario RSS sobreviven al borrado/recarga.

**Reanalizar** conserva la noticia y archiva la generación anterior de resultados. Crea un trabajo nuevo con consultas JEV nuevas, sin reiniciar los intentos antiguos. Los reintentos y la caché quedan separados por generación; reclamar el mismo trabajo no duplica consultas. Hasta finalizar, la exportación del lote queda pendiente. **Historial de análisis** en la noticia permite consultar versiones previas y, si está abierto, se actualiza automáticamente al cambiar la generación o terminar el análisis, sin recargar la página; las exportaciones y el ranking usan únicamente la generación vigente. No utilizar reanálisis para ajustar preguntas o reglas a respuestas retenidas.

La implementación no borra datos ni reanaliza lotes automáticamente como parte del despliegue.

La ficha, el historial y los votos presentan decisiones con palabras: **Riesgo detectado / Sin riesgo detectado** y **Urgente / No urgente**. Una decisión ausente se muestra como **sin determinar**.

## Contraste RSS con tres evaluaciones JEV

En una noticia RSS ya analizada, el presentador puede pulsar **Contrastar con 3 JEV** y confirmar **Iniciar contraste**. Se encolan tres evaluaciones nuevas del mismo modelo jev-1.13.0, con la política y preguntas existentes, sin reutilizar el resultado del análisis original. Máximo 18 peticiones por contraste incluidos reintentos (hasta seis por evaluación); la segunda etapa se omite si no hay candidatos. Cada voto se guarda antes de continuar y la UI muestra progreso, motivos, decisiones, acuerdo y consumo de ese contraste. Las consultas nuevas usan el permiso ilimitado vigente; una reserva antigua no evita registrar el consumo ni el cupo del día actual. Al reanalizar una fuente se eligen sus versiones vigentes.

El resultado es **auxiliar**: no altera el análisis vigente, prioridad, alarmas ni exportaciones del reto. Dos votos coincidentes no se convierten en una confianza del 100 %. Los fallos no cuentan como N ni como un voto «sin revisión»; detienen el contraste y exigen diagnóstico cuando corresponde. La revisión por falta de datos, evidencia o ambigüedad sigue visible.

Diagnóstico real previo al cambio: 37 RSS, 23 revisión/14 completadas; 16 noticias con event_type_confidence_low y 17 con event_state_confidence_low, con solapamiento. No se retocan umbrales para reducir esos contadores. [TypeSafe Confidence](https://docs.typesafe.ai/confidence) explica que confidence resume la distribución de opciones: repetir el mismo modelo puede conservar la misma incertidumbre y no equivale a contar con tres expertos independientes.

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

## Resumen por origen y LiveDay

En **Resumen → Origen de los datos** se puede seleccionar cualquier archivo importado o una de las seis fuentes RSS. La selección cambia al contexto correspondiente y filtra indicadores, ranking y últimas señales. El ranking conserva los 40 proveedores y calcula la prioridad con las evidencias seleccionadas; una recuperación vigente no se deshace por filtrar una fuente anterior. Las alertas del encabezado siguen siendo las del contexto completo.

Una carga correcta abre Resumen, cambia a Ejercicio y selecciona el lote cargado. **Analizar** encola los pendientes y muestra Encolando/Analizando; los contadores se actualizan cada tres segundos. **Exportar** se habilita cuando termina el lote sin errores. Un lote completo ofrece **Reanalizar lote**, con revisión del alcance y confirmación; conserva el historial y efectúa consultas nuevas. LiveDay está habilitado y usa las preguntas congeladas del ejercicio.

Se guarda el nombre del archivo a partir de esta versión. Para lotes anteriores sin ese dato se muestra el tipo y un identificador: no se inventa el nombre original. Volver a cargar el mismo archivo completa ese metadato sin duplicar noticias ni ejecutar análisis automáticamente.

## Perfil RSS `rss-2.0.0`

- Antes de una evaluación RSS se intenta obtener texto editorial público del dominio de su fuente configurada. Se respetan robots.txt, HTTPS, límites técnicos de tamaño/tiempo y redirecciones permitidas. No se usan cookies, credenciales editoriales ni mecanismos para sortear muros de pago. Si falla, se conserva el resumen con estado y motivo explícitos.
- La noticia conserva el resumen original y un snapshot separado de texto ampliado, fecha de consulta, URL, método y hash de contenido. Se reutiliza durante una hora para que reintentos y votos próximos consulten la misma evidencia. La UI muestra la fecha real de obtención, no la fecha del último voto.
- Primera etapa: 40 preguntas Noul de identidad y otras 40 de exposición, además de evento operativo/tipo/estado. La exposición exige coincidencia de operación; para transporte, ruta y modalidad. El vínculo se obtiene con el máximo de identidad/exposición, sin sumar probabilidades ni suponer independencia.
- Segunda etapa: continuidad del suministro, urgencia, severidad, impacto, evidencia literal y duración. Una subida de tarifas por sí sola no demuestra interrupción; los retrasos o cancelaciones deben estar descritos. La cartera es simulada y no se presuponen embarques de Helixa.
- Umbrales, fórmula, modelo y condiciones de sonido permanecen. Metadatos inciertos del tipo/estado se muestran como observaciones. Si el riesgo está claramente descartado, las dudas sobre severidad/impacto/evidencia/duración son descriptivas. Una decisión ambigua, un riesgo con evidencia débil, un resumen truncado sin ampliación o datos de inventario/catálogo faltantes mantienen la revisión. Riesgo positivo contradicho por ausencia clara de evento operativo también exige revisión.
- Los resultados viejos no se sustituyen automáticamente. Reanalizar una noticia RSS aplica el perfil nuevo y archiva la generación anterior. El contraste de tres JEV sigue siendo auxiliar y no sustituye el resultado principal por mayoría.
- Ejercicio conserva preguntas/política1.0.0 y sus exportaciones. La versión RSS nueva está cubierta con casos sintéticos independientes y comprobación real; no se ha establecido una mejora estadística de precisión/recall con una muestra RSS etiquetada independiente.

## Modelo y Analítica

**Modelo**, al final de la navegación (en móvil, menú Más), permite al presentador consultar métricas agregadas cada tres segundos y al recuperar foco. Consultar no encola trabajos ni llama JEV. Las etiquetas y respuestas individuales de referencia no se exponen. Elegir el lote de evaluación: entrenamiento se identifica como desarrollo, validación como comprobación retenida; Test/LiveDay sin etiquetas válidas muestran No calculable, no cero.

Riesgo y urgencia muestran precisión, recall, F1, número de positivos y matrices de confusión. Proveedores muestra métricas micro y coincidencia exacta del conjunto. La evaluación principal incluye noticias en revisión; las cohortes automática/en revisión indican sus denominadores. Lotes incompletos o que mezclan modelo/preguntas/política quedan bloqueados, sin aparentar una evaluación completa. Las métricas sin denominador son No calculable. Modelo/preguntas/política y tamaño de muestra acompañan el resultado vigente; una muestra pequeña no establece precisión general ni valida RSS2.1.

Ejecución de JEV permite elegir archivo o fuente del contexto: peticiones, reintentos, errores, caché, trabajos, tokens reportados, latenciaHTTP por intento y duración registrada de análisis vigente sin cola. Peticiones y tokens incluyen generaciones anteriores/contrastes de las noticias conservadas; no se atribuyen noticias borradas a una fuente que ya no podemos identificar. Se informa qué llamadas carecen de uso, sin estimar coste. Las latencias RSS anteriores a2.1 pueden excluir extracción editorial; desde2.1 se incluye en la duración del análisis. Los percentiles usan interpolación lineal.

Consistencia de tres evaluaciones usa solo el último contraste completo por noticia de la generación vigente, excluye errores y versiones mezcladas. El acuerdo del mismo modelo no es precisión. Analítica conserva ingestión, estados, porcentajes de revisión/automatización, motivos de revisión contados una vez por noticia y cobertura de texto público/parcial/resumen/sin registro. Ninguno de esos porcentajes sustituye una evaluación con etiquetas.

En Resumen, Origen de los datos incluye **Solo noticias reales · todos los RSS** y **Solo datos base · todos los Excel**, además de archivos y fuentes individuales. Cada grupo cambia al contexto correspondiente; no se mezclan noticias reales y ejercicio.

## Categorías RSS2.1 y avisos forestales GDACS

El perfil `rss-2.1.0`, taxonomía `rss-events-1.1.0`, distingue **Incendio forestal** (`wildfire`), incendio industrial/de instalaciones (`fire_incident`) y otros fenómenos naturales. Los incendios forestales se mantienen como `natural_disaster` en el campo canónico por compatibilidad y llevan categoría precisa/confianza/taxonomía en `event_classification`. No se alteran preguntas del ejercicio ni sus métricas/exportaciones.

Para noticiasGDACS con URL oficial `eventtype=WF`, se añade al contexto el código y significado documentado como evidencia del editor; JEV sigue clasificando. No se convierte ese código en riesgo/urgencia ni se asigna automáticamente un proveedor por país. Green describe nivel de alerta y no cambia el tipo de evento: [modelo forestal oficialGDACS](https://www.gdacs.org/Knowledge/models_WF.aspx). La ficha muestra tipo y confianza por separado, también confianza histórica cuando está registrada. Los avisos de confianza no se presentan como si fueran una categoría del evento. Las noticias ya analizadas necesitan reanálisis para incorporar la nueva taxonomía; se conserva la generación anterior.
