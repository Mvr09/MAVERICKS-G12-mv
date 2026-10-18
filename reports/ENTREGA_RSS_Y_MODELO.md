# Entrega revisable: RSS y selección del candidato

URL: https://mavericks-g12-mv-production.up.railway.app

## Cambios visibles

- Noticias: «Analizar esta noticia» encola solo el artículo elegido y muestra progreso real; resultado explicado en lenguaje de compras.
- Consulta de exposición potencial: proveedor, cita literal e hipótesis explícitos. Editable, copia y TXT; persistencia de fuente/generación/versión. No envía mensajes, crea pedidos ni convierte la hipótesis en vínculo del modelo.
- Ficha: consultas guardadas separadas de incidentes y asociaciones deJEV; enlace a noticia y retorno con contextoRSS.
- Modelo, solo presentador: comparación histórica de candidatos, incluidas predicciones revisadas, TP/FP/FN, precisión/recall/F1, cobertura automática y sus errores.
- Diálogo centrado, foco conservado, controles táctiles, estados y textos sin evidencia vacía. Capturas finales en390/1440; comprobación también360/768.

## Modelo: elección y limitaciones

SELECCION_OPERATIVA.md y candidate-selection.json contienen las métricas completas. Sobre las mismas30noticiastraining, proveedores TP/FP/FN:1.0=13/1/9;2.2=17/0/5;3.0=21/2/1;3.1=22/4/0. Se incluyen revisadas. En3.0/3.1, los7automáticos no contienen positivos de riesgo:0errores/7 no acredita mitigación automática segura.

3.0 es el punto de partida preferido para desarrollo asistido por su reducción de omisiones críticas y de fuente única.2.2 referencia de precisión.3.1 recupera servicio marítimo, pero también asocia noticias sin interrupción y conserva fallos sintéticos de riesgo/urgencia.4.0.1 mejora controles pero omite5asociaciones, una fuente única. **Ninguno se promociona al predeterminado1.0.0.**3.0/3.1/4 son internos;2.2 sigue experimental público. No se usa validation como nueva evaluación ni test/LiveDay para mejorar candidatos.

A06 permanece fallido: capacidad múltiple acreditada, calidad de vínculo pendiente; provinciaS003 desconocida. La próxima corrección debe exigir soporte de que el servicio compatible está afectado, separado de compartir región o mercado. No se reduce el umbral, inventa ruta ni ajusta porNews_ID.

## Recorrido real, cuatro minutos

Guion: docs/09_DEMO_PROCUREMENT.md. Evidencia: rss-flow-evidence.json.

1. Sincronización real de seisRSS desdeRailway:2HTTP200/4HTTP304, trabajos terminados.
2. Loadstar: «News in Brief Podcast | Week41 2026 | Congestion, cyber threat, and capacity constraint», texto público consultado200. Un análisis manualJEV1.13/rss2.2:1HTTPnuevo/0caché, resultadoSin riesgo/No urgente/sinproveedores.
3. Consulta manual aOceanbridge sobre servicio declaradoAsia–Europa marítimo: criticidadMedia, nofuenteúnica, lead35días, inventarioNo aplicable, productosNo mapeados; alternativo no implica disponibilidad. Hipótesis pendiente, no asociación confirmada porJEV.
4. Cita literal+hipótesis→edición/guardar/TXT→recuperar. Una consulta real persistente; móvil reutiliza la misma. Ningún envío externo. Copia conreadback y persistencia trasredeploy comprobados.

Ensayos: escritorio1440=240,011s y móvil390emulado=240,008s con pausasdelectura, no benchmark de procesamiento ni estudio de usuarios. No se fabrica alertaRSS para este artículo. Exportación existente descargada200, sin nuevo análisisLiveDay.

Capturas:

- [Noticia en escritorio](rss-final-article-1440.png)
- [Ficha en escritorio](rss-final-supplier-1440.png)
- [Consulta en móvil](rss-final-draft-390.png)
- [Noticia en móvil](rss-final-article-390.png)

## Pruebas y consumo

83unit/integraciónsintética pasan;4E2ERSS360/390/768/1440 yQA pasan;build/paquete, migración0008preserva borradorantiguo y reconecta nuevo. HTTPS, salud/readiness,assets,catálogo40,fichas,worker compatible y permisos401 comprobados; rss-final-verification.json y rss-final-ui.json. Sinoverflow/erroresJS; foco conservado ycopiar/TXT/recuperación funcionales.

Desarrollo:150HTTPnuevos(149HTTP200/1HTTP400 diagnosticado),0reintentos,contador381→531;3.1reutiliza57etapas válidas porhash. RailwayRSS:1nuevo,contador48→49. Totalentrega151intentos; sin reiniciar contadores. RSSperiódicodepago siguefalse. No se necesita ni se propone más consumo en esta entrega.

A14cerrado por confirmación física del usuario, ordenadorFirefox, una alertaQAautomática tras activar sonido, sinProbaralarma. No nuevo ensayo físico móvil. A20heredado deb4d697b:14filas/7,888295967s/23nuevas/0caché/0reintentos; motor/exportación pertinentes sin cambios.19criteriospasan/1fallaA06; matrizACEPTACION_ACTUAL.md. No pendientes delpanelRailway para estas funciones; persiste limitación de modelo/datos y no se ha medido comprensión con compradores.
