# Aceptación consolidada · 18-10-2026

## Versión y criterio de lectura

Aplicación publicada y comprobada: **b4d697ba138fd63fdf8a219644fe89c66f5eb711**. Los commits posteriores de esta sesión son documentación, sin cambios funcionales. Predeterminado **1.0.0**; **link-2.2.0** experimental. Modelo jev-1.13.0; política1.0.0. Factorial aplazado. Cero llamadas JEV nuevas en esta consolidación.

`AUDITORIA.md` conserva la auditoría y ampliaciones históricas. Esta matriz distingue pruebas actuales, herencia justificada y ejecución no realizada para la versión actual. «Pasa heredado» conserva una prueba funcional del componente sin cambios; no convierte un ensayo antiguo en uno recién ejecutado. A20 se volvió a ejecutar una sola vez con la entrega congelada: el tiempo anterior se conserva como histórico y no sustituye la medición nueva.

La fuente final pertinente quedó fijada antes de LiveDay en final-candidate-freeze.json(64archivos). Estable1.0.0, preguntas/puertas originales y2.2.0experimental intactos. Se preparó geo-1.0.1 con los mismos juicios y enriquecimiento aislado: regresa en training y no se promociona ni se expone como opción pública. La entrega añade controlQA de aviso automático, y la clave de caché de análisis incluye versión del extractor.70unit/integración sintética y5E2E dirigidos pasan; se comprueban web/worker/QA reales después del despliegue. No se ejecuta la suite antigua con los cuatro Excel para desarrollar.

## Matriz A01–A20

| ID | Estado actual | Evidencia, herencia y límite |
|---|---|---|
| A01 | pasa | Catálogo40 comprobado nuevamente enb4d697b;20materiales/6productos y40Noul heredados de auditoría inicial/integración120. Constructor y catálogo sin cambios por el arreglo de duración. |
| A02 | pasa | Importación idempotente de los cuatro esquemas heredada; ampliaciones posteriores verificaron News_Feed y LiveDay habilitado. Importador sin cambios desde la integración amplia. No se reabrieron los originales para esta tarea. |
| A03 | pasa | Exclusión de cinco etiquetas en payload HTTP probada previamente; whitelists intactas. Nuevas pruebas unitarias de preparación de duración conservan la separación. Se hereda la prueba con centinela; no se envían etiquetas a JEV. |
| A04 | pasa | Homónimos/geografía inocua cubiertos en unitarias e integración y sintéticos almacenados; sin nuevo atajo por keywords. Matching/normalizadores sin cambios en12c4dff. Muestra histórica limitada, no precisión perfecta. |
| A05 | pasa | Positivas con identidad y riesgo/urgencia negativos cubiertas por integración; soporte negativo verificado en19unit de contrato. Puertas y polaridad intactas. |
| A06 | **falla** | Capacidad funcional de cuarentaNoul y selección múltiple comprobada. Modelo: enriquecimiento aislado no recupera la exposición respaldada; la puertaA sigue rechazándola. Datos: otra identidad mantiene provincia desconocida y posible exposición pendiente. Training:0asociaciones recuperadas/2correctas perdidas/1falsa eliminada/0falsas nuevas, por lo que la variante no pasa a estable. Caso retenido/regresiones por noticia en privado; GEOGRAFIA_AISLADA.md agregado. No se fuerza una etiqueta ni se exige precisión perfecta en todas las noticias. |
| A07 | pasa | Agrupación de titulares e incidentes/máximo por proveedor heredada de integración y sondeos reales. Incidentes y deduplicación sin cambios; no se suma la nueva duración al score como factor independiente. |
| A08 | pasa | Recuperación compatible, historial y recepción tardía cubiertos por integración. Código de reconciliación y cierre intacto; evidencia heredada, sin cerrar incidentes reales para probar otra vez. |
| A09 | pasa | Inventario físico desconocido/no aplicable/cero probado previamente; scoring intacto. El extractor no inventa stock o lead time. Pruebas nuevas conservan duración desconocida cuando no es utilizable. |
| A10 | pasa | Fórmula y referencia congeladas, severidad y confianza separadas; hereda suite de referencia/integración.42pruebas originales de duración +2de preparación/caché pasan;6sintéticos JEV verifican dos días exactos/mínimos sin alterar pesos ni puertas. |
| A11 | pasa | Ingesta/análisisRSS real previo conservado. Enb4d697b, seis trabajos de consulta reales done,2HTTP200/4HTTP304 y fechas actualizadas;304 son respuestas condicionales, no cuerpos nuevos. Pago periódico false; contadorJEVRSS48→48 en esta comprobación. |
| A12 | pasa | RSS/Atom,304, GUID actualizado, versiones, duplicados y XML peligroso heredados de integración. ParserRSS/versionado sin cambios. Consulta del worker actual confirma operación, sin presentar ese sondeo como nuevo ensayo de todos los casos negativos. |
| A13 | pasa | Adaptador/reintentos heredados; nuevas pruebas de dispatch/caché con MockTransport y catálogo sintético. Ensayo geográfico real62HTTP200 y final23HTTP200, sin reintentos; errores no se convierten enN. Contadores históricos/cachés conservados. No se afirma que haya ocurrido un fallo externo nuevo. |
| A14 | pasa | Usuario confirma ordenador/Firefox: Activar sonido → QA5s → una sola alerta automática audible, sin Probar alarma. Complementa lógica acreditada de mute/cooldown/historial/revisión/foco/bloqueo y prueba Railway real del mismo audio.notify. EscenarioQA separado del clasificador. SO/versión no indicados. |
| A15 | pasa | Borrador alternativo real editado, guardado, copiado y TXT descargado; proveedor directo probado en integración. Generador y persistencia sin cambios. No se repite una mutación real sin necesidad ni se inventa capacidad del alternativo. |
| A16 | pasa | Formato/orden/IDs/Y-N/exportaciones históricas heredados; exportador sin cambios. La medición final autorizada añade una exportación LiveDay de14filas con contrato y orden comprobados, sin evaluar precisión ni ajustar con sus respuestas. |
| A17 | pasa | Esquema0007 y worker compatibles después del redeploy. A20 conserva generaciones previas y verifica hashes de todos sus resultados históricos; nuevas14filas/exportación200. Cola/leases/concurrencia heredan integración sin cambios. No se borró historial ni se reiniciaron contadores. |
| A18 | pasa | HTTPS, cuatroassets, catálogo40 y ficha200 enb4d697b. QA anónimo401 y presentador202 real; sesión/CSRF heredados.31archivos del push/paquete74 revisados sin secretos ni originales/cambios ajenos. SeñalQA temporal de pestaña aislada de registros de cartera. |
| A19 | pasa | Perfil/revisión4E2E y nuevoQA dirigido pasan. UIQA pública real360/390/768/1440 sin overflow/erroresJS, contextoRSS/ficha y una entrega automática. Emulación Chrome no equivale a Firefox físico ni móvil físico; se conserva ese límite. |
| A20 | pasa | Medición final única18-10-2026, commitb4d697b, perfil1.0.0/modelojev-1.13.0/extractorduration-1.1.0:14filas y Excel recibido en7.888s con relojmonotónico desdePOST, incluidos cola/reintentos/descarga.23HTTP200 nuevas/0reintentos/0etapas cacheadas/0artículos íntegramente cacheados; historial/orden/IDs conservados. a20-current-results.json. No mide precisión ni se usa para ajustes. |

**Balance actual:19 pasa (incluida herencia explícita),1 falla(A06),0 pendientes. No hay aceptación completa.** A20 ya tiene medición nueva de esta entrega; su antecedente histórico continúa separado.

## Cierre acotado de A06

La selección múltiple existe y no está implementada con una Choice de proveedor único: hay cuarentaNoul y B procesa varios candidatos. El caso fallido concreto se conserva en privado con noticia, texto, referencia, predicción y puertas. El candidato experimental recupera una asociación con región verificable, pero no puede determinar la provincia de la ubicación ambigua a partir del resultado esperado.

**Dato concreto necesario del propietario:** para S003, confirmar ubicación operativa de Taizhou: provincia Jiangsu o Zhejiang (o dirección/coordenadas y fuente de confirmación). El gazetteer ofrece alternativas, no plantas ni decisiones empresariales. Este dato es necesario, pero no garantiza por sí solo que el default acierte: hay que propagarlo de forma versionada al contexto efectivo y comprobar el comportamiento con training/sintéticos. La referencia no se modifica para declarar éxito.

La otra omisión del default tiene geografía resoluble con datos ya disponibles: el enriquecimiento y la confirmación independiente ya existen en2.2.0 y fueron desarrollados con training. No se copia silenciosamente ese perfil al default ni se ignoran sus regresiones. Sin un defecto nuevo determinista demostrado, no se añade una excepción o un parche de decisión ajustado al caso retenido.

No hace falta que todo el training tenga precisión perfecta para demostrar selección múltiple. Sí hace falta resolver y comprobar el alcance de este caso antes de declarar A06 aprobado. El factorial no es condición de cierre y continúa aplazado.

## Comprobaciones históricas de la consolidación previa (12c4dff)

Este apartado conserva la fase anterior: los contadores y la ausencia de nuevas llamadas descritos aquí no corresponden al ensayo final posterior.

- Atribución offline de la omisión desde el diagnóstico guardado, no nueva inferencia/evaluación de validation.
- Verificación de la ambigüedad de provincia en el snapshot existente y correspondencia única de la otra ciudad.
- Controles training y sintético multproveedor reutilizados: el experimental conserva los tres IDs esperados. Se conservan sus errores y regresiones ya documentados; no se recalculan métricas retenidas para escoger cambios.
- Revisión del delta de producto y hashes de preguntas/política; ninguna modificación funcional nueva, por lo que no se repitieron ingestión, mutaciones, evaluación retenida ni suites con Excel.
- MetadatosA20 extraídos del informe histórico: filas/fechas/commit/perfil y llamadas, sin leer celdas o respuestas LiveDay. No se abrió answer key.
- Cero nuevas peticionesJEV; cupo dirigido de duración conserva12/36, contador local253 registrado. No se reutiliza ese cupo específico para otros artículos. RSS de pago periódico false.

## Actualización final de esta entrega

La geografía aislada se comprobó sin cambiar preguntas/umbrales y no supera la regresión: no se activa en estable. La capacidad funcional de múltiples asociaciones se distingue de los errores de interpretación del modelo y de la provincia desconocida. N044 solo retrospectiva posterior a congelación; no se modificó código de inferencia después de sus resultados.

LiveDay se ejecutó de nuevo únicamente al terminar desarrollo y congelar la entrega, por autorización explícita: una medición de14filas, no una segunda evaluación independiente. Se inspeccionaron formato, metadatos y conservación de historial, no referencias para corregir el modelo.0nuevas ejecuciones de test/validation completas.

Comprobaciones reales posteriores al push: final-qa-railway-verification.json(6trabajosRSS done,2HTTP200/4HTTP304,0JEVRSS),qa-automatic-railway.json(backend real/sondeo/oscilador, no audibilidad física) y a20-current-results.json. Datos protegidos y Excel permanecen fuera de Git/Docker. Factorial aplazado.

## Entrega procurement y candidato semántico

A14pasa tras la confirmación física explícita: ordenador/Firefox, activar sonido→QA5s→una emisión automática audible sin Probar alarma. El control sigue el mismo notificador y se ha plegado bajo herramientas de presentador; no se modificó audio.ts. El balance es19pasa/1falla(A06).

La nueva mesa/ficha/alertas conectan prioridad, evidencia, material/productos y siguiente acción. La ficha conserva el origen seleccionado por URL y consulta con ese origen: no mezcla la prioridad filtrada con el máximo global. El carril de novedades reserva espacio para no desplazar filtros. El borrador permanece al actualizar la ficha. No se inventan capacidad alternativa, cobertura de una interrupción ni afectación confirmada.

Candidato link-3.0.0-dev: desarrollo30training+6sintéticos,66HTTP200/0reintentos; TP/FP/FN y métricas en LINK_3_DESARROLLO.md y link-3-results.json. No promoción: mejora recall pero introduce asociaciones falsas y regresiones emparejadas. A06 continúa fallido por calidad de vínculo/decisión, separada de la capacidad funcional y de la provinciaS003 desconocida. No se consultaron conjuntos retenidos para este desarrollo.

A20heredado de medición única enb4d697b(14filas/7,888s/23nuevas/0caché). procurement-a20-inheritance.json acredita13dependencias intactas: motor estable, duración, política, cola, exportación y perfil. El único cambioAPI es filtro opcional enGET de ficha; no se modifica el recorrido medido ni se lanza otroLiveDay. No se atribuye un nuevo tiempo a la entregaUI.
