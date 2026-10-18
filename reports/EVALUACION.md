# Evaluación del motor · estado consolidado18-10-2026

## Versiones y separación

Predeterminado1.0.0 y experimental link-2.2.0; política1.0.0/modelo jev-1.13.0. No se promueve una versión por reducir revisión. Las preguntas/umbrales congelados no se modificaron en el cierreA06. [Matriz de aceptación actual](ACEPTACION_ACTUAL.md).

La primera comprobación autorizada se realizó con tres identidades de training (4HTTP200,1,476s locales), documentada en jev-local.json. El estado inicial «validación/test/LiveDay no ejecutados» dejó de ser vigente durante la fase final del17-10-2026: validation10, test20 y LiveDay14 se ejecutaron con1.0.0; fechas, versión y exportación constan en final-execution-summary.json. Las flagsfalse en prompt-freeze.json describen la congelación previa; ese artefacto histórico no se reescribe.

## Qué se evaluó

Validation histórica n=10: riesgo TP3/FP0/FN2/TN5, F1=0,75; urgencia F1=1,00 con2positivos; conjuntos de proveedores exactos8/10;8noticias en revisión. No se presentan esos resultados como una nueva evaluación independiente ni como precisión general del producto. Test/LiveDay no tienen métricas de exactitud calculadas con answer key: no se buscó ni utilizó. Su ejecución final y formato de exportación no equivalen a una evaluación supervisada de acierto.

El desarrollo posterior de vínculo se hizo con30training y sintéticos; se congeló2.2.0 antes de una comparación retrospectiva de la validation ya inspeccionada. Se conservan las regresiones y el falloA06 del default; no se vuelve a ajustar con ese caso. Véanse LINK_V2_PROPUESTA.md y AUDITORIA_SOPORTE.md. Los datos por noticia/referencias permanecen en reports/private, fueraGit/Docker/frontend.

El ensayo dirigido de duración posterior usó solo seis sintéticos:6/6duraciones,12HTTP200/0reintentos de36máximo; no cambia la conclusión de matching ni acredita una mejora de precisión. Consumo, uso y límite en DURATION_RESULTADOS.md. El factorial sigue aplazado.

## LiveDay y RSS

LiveDay se ejecutó **el17-10-2026**, no durante el desarrollo posterior del18-10. [A20_HISTORICO.md](A20_HISTORICO.md) registra14filas,5,753s, commit4a3645a,23peticiones HTTP nuevas y límites de caché/reloj. No se reabre ni ejecuta LiveDay para corregirA06. El tiempo histórico no certifica12c4dff: A20actual queda no ejecutado, con antecedente aprobado.

RSS conserva datos reales y exposición potencial de una cartera simulada; no modifica exportaciones del ejercicio. Consultas del worker en12c4dff:seis trabajos completados,2HTTP200/4HTTP304, sin llamadas JEV adicionales. Inferencia periódica de pago=false. No existe evaluación RSS independiente etiquetada con la que afirmar precisión/recall. Mocks y acuerdo entre ejecuciones no sustituyen esas etiquetas.

## Entrega posterior congelada y A20 nuevo

Geografía aislada a preguntas originales:30training+6sintéticos,62HTTP nuevas con44etapas previas reutilizadas, una comparación retrospectiva después de congelar. No se promociona por regresiones (GEOGRAFIA_AISLADA.md). Default1.0.0 y2.2.0experimental permanecen.

Tras acabar ese desarrollo, el18-10-2026 se ejecutó una sola medición final LiveDay autorizada enb4d697b:14filas,7,888s monotónicos,23HTTP nuevas/0caché, historial íntegro. No se calcula exactitud ni se ajusta con sus salidas. El antecedente17-10 sigue separado y ninguna descripción previa de «A20actual no ejecutado» representa el estado después de esta nueva fase final.
