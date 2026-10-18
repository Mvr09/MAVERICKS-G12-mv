# Selección operativa · 18-10-2026

**Preferido:3.0 para descubrimiento asistido con revisión humana. Referencia de precisión:2.2. Predeterminado reproducible:1.0.0, sin promoción automática.** No se decide por una regresión aislada ni por F1. El coste de omitir proveedores críticos/fuente única y el soporte de las acciones importan; no se inventan ponderaciones monetarias ni ahorros.

## Resultados almacenados:30training, incluidas todas las revisadas

| Medida |1.0|2.2|3.0|
|---|---:|---:|---:|
|Riesgo TP/FP/FN|10/0/4|12/0/2|11/0/3|
|Riesgo precisión/recall/F1|1/.714/.833|1/.857/.923|1/.786/.880|
|Urgencia TP/FP/FN|5/3/0|5/0/0|5/1/0|
|Urgencia precisión/recall/F1|.625/1/.769|1/1/1|.833/1/.909|
|Proveedores TP/FP/FN|13/1/9|17/0/5|21/2/1|
|Proveedores precisión/recall/F1|.929/.591/.722|1/.773/.872|.913/.955/.933|
|Conjuntos exactos|25/30|26/30|28/30|
|Revisión|16/30|22/30|23/30|
|Cobertura automática|14/30|8/30|7/30|
|Errores conjuntos entre automáticos|2/14|0/8|0/7|
|Positivos de riesgo de referencia entre automáticos|4|0|0|
|Asociaciones omitidas de criticidad alta|2|1|0|
|Asociaciones omitidas de fuente única|1|1|0|

Misma referencia/suplidores/modelo/política;2.2 almacenado precede a duration-1.1.0. No es un ensayo causal de una pregunta ni evaluación independiente. El cero de errores automáticos de2.2/3.0 no acredita automatización de riesgos positivos: no hay positivos en esos subconjuntos. TP/FP/FN y conjuntos incluyen siempre casos en revisión. Agregados reproducibles: scripts/compare_stored_candidates.py y candidate-selection.json. Datos por noticia exclusivamente privados.

## Balance de las tres discrepancias de3.0

El diagnóstico exacto, noticias y referencias está en reports/private/DIAGNOSTICO_OPERATIVO_3.md y candidate-operational-errors.json.

- **Vínculo correcto perdido:** servicio marítimo con ruta y modo explícitos en el material. La pregunta de área mezcla ubicación física con corredor; su respuesta baja bloquea la asociación pese a compatibilidad de operación y evidencia de servicio altas. Criticidad media, no fuente única, inventario no aplicable; productos no mapeados. La omisión retira la señal del ranking y puede evitar la consulta sobre plazos. No debe interpretarse como ausencia de amenaza. Es resoluble semánticamente sin inventar embarques.
- **Primera asociación adicional:** envase primario, criticidad alta, varias fuentes y un producto mapeado. Probabilidades de asociación/operación en frontera, sin fragmento seleccionado, riesgoN/urgenciaN. Añade trabajo de revisión/consulta sobre un producto; no genera interrupción confirmada ni mitigación automática. No se debe inferir dependencia de barcazas de un fabricante de vidrio.
- **Segunda adicional:** distribuidor de productos químicos, criticidad media, varias fuentes, productos no mapeados; riesgoY, prioridad34,2 y revisión. La referencia no lo incluye, pero el catálogo tampoco afirma ni excluye transporte fluvial. Cuenta comoFP en las métricas; operativamente es una hipótesis insuficientemente respaldada, no una exclusión demostrada. La acción adecuada es confirmar ruta/modo y alcance, sin reservar capacidad alternativa ni afirmar retrasos de Helixa.

3.0 reduce omisiones relevantes frente a2.2, a cambio de dos asociaciones adicionales revisadas y menor cobertura automática. Se selecciona para el próximo desarrollo supervisado, **no para cambiar el default ni liberar avisos sonoros/mitigación**. El borrador de verificación facilita obtener la información que falta, sin ocultar estos errores ni convertir una duda en un hecho. No se ha habilitado3.0 como perfil público de producción.

## Corrección ensayada4 y qué demuestra

Se separó `min(sitio,operación)` del servicio explícitamente declarado en catálogo: exposición=max(ambos), identidad independiente, riesgo nunca crea vínculo. Se reutilizó el criterio2.2 de riesgo/urgencia y se aclaró soporte factual condicional. Umbrales y prioridad empresarial intactos; no hay excepciones por noticia.

4.0 completó30training+6sintéticos y se detuvo anteHTTP400 en el control marítimo adicional. PeticiónB197576bytes/154preguntas; proveedor sin motivo concreto. Tamaño/contexto es hipótesis. Se conservó el error y se diagnosticó antes de continuar.4.0.1 elimina copias del catálogo en cada pregunta, manteniendo los textos de las proposiciones y el catálogo compartido. Es otra representación/versionado, no se mezclan sus predicciones con4.0. No se eligió una respuesta favorable repitiendo casos con el mismo payload.

4.0.1 completó30training+8sintéticos. Riesgo12/0/2, urgencia5/0/0; proveedores17/2/5, precisión.895/recall.773/F1.829, conjuntos27/30. Revisión20, automático10/30 con0errores conjuntos y3positivos de riesgo correctos. Sus cinco omisiones incluyen una fuente única y sus dos falsas asociaciones son de criticidad alta. No supera el balance de3.0; no se promueve pese a su mayor cobertura automática.

Los controles nuevos distinguen mar/ferrocarril y ambos se vinculan al servicio adecuado con riesgoY/urgenciaN, en revisión. Interrupción parcial: vínculo objetivo/riesgoY/urgenciaN, en revisión. Multiubicación conserva tres; negativos geográficos/homónimos no vinculados. La ciudad ambigua sigue en revisión; no se declara confirmada provincia ni afectación individual deS003. Estos controles prueban capacidades, no que el default haya resueltoA06 ni generalización fuera de desarrollo.

A06 sigue fallido en producción: la geografía verificada no basta para la pregunta original y los candidatos no justifican aún una promoción integral. Se distingue capacidad funcional multproveedor, errores del modelo e información operativa ausente. No se ha reejecutado la comparación retrospectiva ni test/LiveDay.

## Consumo y evidencia

150HTTP nuevos locales,149HTTP200/1HTTP400,0reintentos;68para4.0,69para4.0.1 y13para3.1, dentro del presupuesto228 compartido y persistente. Contador381→531. Preguntas/hash congelados, resultados válidos y usos reportados conservados. El experimento incluye cambios de contexto/riesgo/revisión: no se atribuye causalidad aislada. El factorial continúa aplazado. RSS manual tiene su registro separado y sigue desactivado el análisis periódico de pago.

## Corrección mínima3.1: resultado completo, sin promoción

Se mantuvieron A y todas las preguntas de3.0, añadiendo solamente una pregunta de servicio declarado para candidatos Logistics. Sin candidatos logísticos, B es idéntico a3.0. Riesgo/urgencia/umbrales/política intactos; todos los riesgos positivos requieren confirmación humana. Es un experimento interno, no un perfil seleccionable de producción.

30training+8sintéticos,13HTTP nuevos/57etapas válidas cacheadas,0reintentos. Riesgo12/0/2, precisión1/recall.857/F1.923; urgencia5/1/0, .833/1/.909; proveedores22/4/0, .846/1/.917; conjuntos27/30. Revisión23/30, automáticos7/30 y0errores conjuntos, sin positivos de riesgo automáticos. Incluye todas las predicciones revisadas.

Recupera el servicio marítimo omitido y elimina los FN de proveedor en esta muestra. A cambio añade una falsa asociación logística de criticidad alta y otra media, ninguna fuente única ni con productos mapeados; ambas riesgoN/urgenciaN/prioridad0 y revisión. La primera noticia trata de cambio de divisas, la segunda de un acuerdo comercial: compartir región/mercado no demuestra exposición a un evento disruptivo. No disparan alertas o mitigación, pero sí pueden desperdiciar tiempo del comprador. No se descarta3.1 por estas dos regresiones aisladas: se considera su ganancia de cobertura, coste de revisión y gravedad de las acciones. Persiste además riesgoN en interrupción parcial sintética y urgenciaY en el desvío marítimo, frente a4.0.1 riesgoY/urgenciaN y riesgoY/urgenciaN respectivamente. No todo el delta puede atribuirse al nuevo campo: JEV resuelve conjuntamente B y también cambian respuestas preexistentes.

**Decisión:**3.0 permanece como punto de partida de desarrollo supervisado;2.2 como referencia de precisión.3.1 demuestra cómo recuperar el corredor, pero no prueba aún que servicio compatible sea servicio afectado. Ninguno sustituye al predeterminado1.0.0. No se cambian umbrales para recuperar casos ni se fuerza asociación con etiquetas esperadas.

La siguiente corrección debería distinguir factualidad del evento, compatibilidad del servicio y exposición sustentada, conservando incertidumbre cuando falta ruta o modo. Primero, controles de entrenamiento/sintéticos de noticias comerciales sin interrupción frente a interrupción explícita del mismo corredor, manteniendo riesgo/urgencia originales. No se ejecuta otra ronda ni se abre el factorial en esta entrega. El catálogoS003 conserva provincia desconocida y productos/rutas no mapeados siguen sin inventarse. Validation solo retrospectiva; no se usa test/LiveDay para este desarrollo.
