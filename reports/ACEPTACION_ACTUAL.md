# Aceptación consolidada · 18-10-2026

## Versión y criterio de lectura

Aplicación publicada y comprobada: **12c4dff59252acca6a122341ae36479c81041b0c**. Los commits posteriores de esta sesión son documentación, sin cambios funcionales. Predeterminado **1.0.0**; **link-2.2.0** experimental. Modelo jev-1.13.0; política1.0.0. Factorial aplazado. Cero llamadas JEV nuevas en esta consolidación.

`AUDITORIA.md` conserva la auditoría y ampliaciones históricas. Esta matriz distingue pruebas actuales, herencia justificada y ejecución no realizada para la versión actual. «Pasa heredado» conserva una prueba funcional del componente sin cambios; no convierte un ensayo antiguo en uno recién ejecutado. A20 se mantiene pendiente para la versión actual porque cambió el extractor que alimenta los payloads de inferencia.

Desde0d6631e (última integración amplia de120backend y13E2E dirigidos) hasta12c4dff, los únicos archivos de producto cambiados son app/analysis.py (reexporta el extractor), app/duration.py (nuevo extractor) y frontend/src/main.tsx (texto aclaratorio de asociación/exposición). Sin cambios en preguntas, umbrales, normalizadores de decisiones, importador, cola, almacenamiento, auth, exportador, audio o contratos. Las huellas de ambas congelaciones de preguntas/política coinciden. Se revisó ese delta para decidir la herencia; no se volvió a ejecutar una suite que importa los cuatro Excel.

## Matriz A01–A20

| ID | Estado actual | Evidencia, herencia y límite |
|---|---|---|
| A01 | pasa | Catálogo40 comprobado en12c4dff;20materiales/6productos y40Noul heredados de auditoría inicial/integración120. Constructor y catálogo sin cambios por el arreglo de duración. |
| A02 | pasa | Importación idempotente de los cuatro esquemas heredada; ampliaciones posteriores verificaron News_Feed y LiveDay habilitado. Importador sin cambios desde la integración amplia. No se reabrieron los originales para esta tarea. |
| A03 | pasa | Exclusión de cinco etiquetas en payload HTTP probada previamente; whitelists intactas. Nuevas pruebas unitarias de preparación de duración conservan la separación. Se hereda la prueba con centinela; no se envían etiquetas a JEV. |
| A04 | pasa | Homónimos/geografía inocua cubiertos en unitarias e integración y sintéticos almacenados; sin nuevo atajo por keywords. Matching/normalizadores sin cambios en12c4dff. Muestra histórica limitada, no precisión perfecta. |
| A05 | pasa | Positivas con identidad y riesgo/urgencia negativos cubiertas por integración; soporte negativo verificado en19unit de contrato. Puertas y polaridad intactas. |
| A06 | **falla** | Caso regional concreto sigue fallando en el predeterminado. Se reconstruyó del diagnóstico ya existente, sin ajustar con validación. Corrección general parcial ya desarrollada en training/sintéticos permanece experimental. Falta confirmar provincia/ubicación operativa de una identidad ambigua; además persiste limitación de interpretación del default para otra identidad con geografía resoluble. Detalle protegido en reports/private/A06_CIERRE.md. No se eleva a requisito de precisión perfecta ni se rebaja el caso para aprobarlo. |
| A07 | pasa | Agrupación de titulares e incidentes/máximo por proveedor heredada de integración y sondeos reales. Incidentes y deduplicación sin cambios; no se suma la nueva duración al score como factor independiente. |
| A08 | pasa | Recuperación compatible, historial y recepción tardía cubiertos por integración. Código de reconciliación y cierre intacto; evidencia heredada, sin cerrar incidentes reales para probar otra vez. |
| A09 | pasa | Inventario físico desconocido/no aplicable/cero probado previamente; scoring intacto. El extractor no inventa stock o lead time. Pruebas nuevas conservan duración desconocida cuando no es utilizable. |
| A10 | pasa | Fórmula y referencia congeladas, severidad y confianza separadas; hereda suite de referencia/integración.42pruebas originales de duración +2de preparación/caché pasan;6sintéticos JEV verifican dos días exactos/mínimos sin alterar pesos ni puertas. |
| A11 | pasa | Ingesta/análisisRSS real previo conservado. En12c4dff, seis trabajos de consulta reales done,2HTTP200/4HTTP304 y fechas actualizadas;304 son respuestas condicionales, no cuerpos nuevos. Pago periódico false; contadorJEVRSS48→48 en esta comprobación. |
| A12 | pasa | RSS/Atom,304, GUID actualizado, versiones, duplicados y XML peligroso heredados de integración. ParserRSS/versionado sin cambios. Consulta del worker actual confirma operación, sin presentar ese sondeo como nuevo ensayo de todos los casos negativos. |
| A13 | pasa | Reintentos401/429/529 y error no convertido enN heredados; adaptador sin cambios desde0d.126campos de soporte cacheados auditados y19unit de contrato pasan. Ensayo nuevo6sintéticos:12HTTP200,0reintentos; no se simula que haya ocurrido un error externo nuevo. |
| A14 | **no ejecutado completo** | Ordenador+Firefox: el usuario confirma sonido mediante **Probar alarma**; aclara expresamente que solo usó ese botón. Audibilidad de una **alerta elegible nueva automática**, no confirmada. Gesto/mute/cooldown/emisión única/historial/foco/bloqueo heredan E2E con mocks, códigoaudio intacto; no acreditan sonido físico automático. Registro en AUDIO_VERIFICACION.md. |
| A15 | pasa | Borrador alternativo real editado, guardado, copiado y TXT descargado; proveedor directo probado en integración. Generador y persistencia sin cambios. No se repite una mutación real sin necesidad ni se inventa capacidad del alternativo. |
| A16 | pasa | Formato/orden/IDs/Y-N/exportaciones reales históricas comprobados; exportador sin cambios. No se afirma una nueva exportación de test/LiveDay ni se reevalúan sus respuestas. El arreglo de duración no cambia el contrato del archivo. |
| A17 | pasa | Persistencia de resultados/exportaciones comprobada tras redeploy histórico; esquema0007, catálogo y fuentes/trabajos observados tras redeploy12c4dff. ModeloDB/migraciones/leases sin cambios; reclamación concurrente y recuperación de lease heredan integración. |
| A18 | pasa | HTTPS/assets/catálogo/ficha actuales200; lectura pública y sincronización con sesión real comprobadas. Auth/origen/CSRF heredados sin cambios; bundle/paquete71archivos y17archivos del push revisados sin secretos ni originales nuevos. |
| A19 | pasa | UI pública real12c4dff a360/390/768/1440, ficha y noticiaRSS, foco contexto, sin overflow/erroresJS. Captura360 revisada visualmente con texto de exposición. Guardia de perfil/revisión heredada de4E2E locales del mismo cambio. No equivale a móvil físico, omitido por el usuario. |
| A20 | **no ejecutado en12c4dff** | **Históricamente pasa:**17-10-2026, commit4a3645a, perfil/política1.0.0,14filas,5,753s hasta Excel.23HTTP nuevas, no replay íntegro. Parser de duración cambió después y puede cambiar B: no extrapolar ese tiempo a12c4dff ni a2.2.0. Repetición únicamente en fase final autorizada, sin desarrollar con LiveDay. Detalle en A20_HISTORICO.md. |

**Balance actual:17 pasa (incluida herencia explícita),1 falla(A06),2no ejecutados completos/actuales(A14/A20). No hay aceptación completa.** La matriz histórica18/1/1 se conserva como histórica; no se borró una prueba ni se afirmó una nueva medición de rendimiento.

## Cierre acotado de A06

La selección múltiple existe y no está implementada con una Choice de proveedor único: hay cuarentaNoul y B procesa varios candidatos. El caso fallido concreto se conserva en privado con noticia, texto, referencia, predicción y puertas. El candidato experimental recupera una asociación con región verificable, pero no puede determinar la provincia de la ubicación ambigua a partir del resultado esperado.

**Dato concreto necesario del propietario:** para S003, confirmar ubicación operativa de Taizhou: provincia Jiangsu o Zhejiang (o dirección/coordenadas y fuente de confirmación). El gazetteer ofrece alternativas, no plantas ni decisiones empresariales. Este dato es necesario, pero no garantiza por sí solo que el default acierte: hay que propagarlo de forma versionada al contexto efectivo y comprobar el comportamiento con training/sintéticos. La referencia no se modifica para declarar éxito.

La otra omisión del default tiene geografía resoluble con datos ya disponibles: el enriquecimiento y la confirmación independiente ya existen en2.2.0 y fueron desarrollados con training. No se copia silenciosamente ese perfil al default ni se ignoran sus regresiones. Sin un defecto nuevo determinista demostrado, no se añade una excepción o un parche de decisión ajustado al caso retenido.

No hace falta que todo el training tenga precisión perfecta para demostrar selección múltiple. Sí hace falta resolver y comprobar el alcance de este caso antes de declarar A06 aprobado. El factorial no es condición de cierre y continúa aplazado.

## Comprobaciones de esta consolidación

- Atribución offline de la omisión desde el diagnóstico guardado, no nueva inferencia/evaluación de validation.
- Verificación de la ambigüedad de provincia en el snapshot existente y correspondencia única de la otra ciudad.
- Controles training y sintético multproveedor reutilizados: el experimental conserva los tres IDs esperados. Se conservan sus errores y regresiones ya documentados; no se recalculan métricas retenidas para escoger cambios.
- Revisión del delta de producto y hashes de preguntas/política; ninguna modificación funcional nueva, por lo que no se repitieron ingestión, mutaciones, evaluación retenida ni suites con Excel.
- MetadatosA20 extraídos del informe histórico: filas/fechas/commit/perfil y llamadas, sin leer celdas o respuestas LiveDay. No se abrió answer key.
- Cero nuevas peticionesJEV; cupo dirigido de duración conserva12/36, contador local253 registrado. No se reutiliza ese cupo específico para otros artículos. RSS de pago periódico false.
