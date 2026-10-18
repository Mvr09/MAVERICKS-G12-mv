# Candidato semántico de matching · 18-10-2026

**link-3.0.0-dev no promovido.** Baseline1.0.0 reproducible y experimental2.2.0 siguen intactos. El candidato se conserva en módulo/runner de desarrollo, sin selector público ni dispatch de producción. No cambia fórmulas, umbrales ni preguntas originales de riesgo/urgencia. No es la promoción íntegra de2.2.0.

## Hipótesis y ejecución

Recuperar ampliamente los candidatos, confirmar en B desde noticia+catálogo/geografía y distinguir soporte positivo del soporte de exclusión. Identidad, área afectada y compatibilidad operativa son juicios independientes: el riesgo condicionado nunca crea una asociación. Una cita no basta para demostrar exposición; ausencia de asociación tampoco prueba exclusión. Los campos auxiliares continúan visibles sin bloquear por sí solos una decisión respaldada.

Protocolo y código congelados en link-3-freeze.json antes de ejecutar30training+6sintéticos. Comparación con resultados almacenados del baseline a igual extractor duration-1.1.0; no se repitió el baseline para obtener una respuesta favorable. No se consultaron validation, test, LiveDay ni answer key. No es una nueva evaluación independiente. Sin cambios posteriores a preguntas para mejorar estas cifras.

| Training completo, incluidas revisadas | Baseline1.0.0 | Candidato3.0dev |
|---|---:|---:|
| Riesgo TP / FP / FN |10 / 0 / 4|11 / 0 / 3|
| Riesgo precisión / recall / F1 |1 / 0,714 / 0,833|1 / 0,786 / 0,880|
| Urgencia TP / FP / FN |5 / 3 / 0|5 / 1 / 0|
| Urgencia precisión / recall / F1 |0,625 / 1 / 0,769|0,833 / 1 / 0,909|
| Proveedores TP / FP / FN |13 / 1 / 9|21 / 2 / 1|
| Proveedores precisión / recall / F1 |0,929 / 0,591 / 0,722|0,913 / 0,955 / 0,933|
| Conjunto exacto |25 / 30|28 / 30|
| Revisión |16 / 30|23 / 30|
| Cobertura automática |14 / 30|7 / 30|
| Errores de salida conjunta entre automáticas |2 / 14|0 / 7|

**No basta el mejor agregado:** nueve asociaciones correctas recuperadas y una perdida; una falsa eliminada y dos falsas añadidas. Dos decisiones de riesgo que el baseline acertaba empeoran, aunque se corrigen tres omisiones y el totalFN baja. Las falsas asociaciones nuevas proceden de respuestas de exposición regional/operativa. La confusión entre compatibilidad y ruta/proceso confirmado es una hipótesis para investigar; estas probabilidades no prueban la causa interna del modelo. Una selección más amplia no demuestra por sí sola exposición. La pérdida de un vínculo logístico y la deriva en riesgo con idénticas preguntas ocurren con contexto y juicios auxiliares diferentes, sin cambio de umbral; no se atribuye causalidad exclusiva al contexto sin un ensayo adicional. Detalle por noticia, respuestas, citas y puertas en reports/private/link-3-development.json, excluido de Git/Docker.

## Sintéticos y revisión

- Varias ubicaciones: recupera los tres proveedores, riesgo y urgencia; conserva revisión por soporte.
- Interrupción parcial: recupera el vínculo objetivo, pero riesgo sigue negativo; no urgente, en revisión. No satisface todavía la expectativa completa.
- Tres negativos de geografía/homónimos: sin asociación, sin riesgo ni urgencia; siguen revisados cuando falta soporte afirmativo de exclusión.
- Ciudad ambigua: la salida incluye una posible asociación y riesgo/urgencia, siempre en revisión. No confirma la provincia deS003 ni permite usar ese resultado como afectación comprobada. Es una limitación que bloquea promoción; no se escoge una provincia para acertar.

La cobertura automática baja: los siete casos automáticos no tienen errores de salida, pero no contienen riesgos positivos. Por tanto0/7 no demuestra seguridad para automatizar riesgos. La revisión por asociación/riesgo/prioridad se desglosa en link-3-results.json por noticias, con solapamiento entre causas. No se eliminan bloqueos para mejorar cobertura. Las tres salidas se evalúan incluso cuando requieren revisión.

## Consumo y decisión

66peticionesHTTP200,0reintentos,0etapas cacheadas nuevas; baseline reutilizado desde resultados existentes, sin atribuirlo a consultas nuevas. Contador local315→381 conservado; presupuesto persistente específico216máximo, sin reiniciar otros contadores. Modelojev-1.13.0; duración/uso/intentopor llamada almacenados en privado. No se activa RSS periódico de pago.

No cumple guardias previas: falsas asociaciones adicionales, pérdida de vínculo correcto y regresiones emparejadas de riesgo. No se expone al presentador como versión preparada para producción ni se cierraA06. Próxima investigación con desarrollo: separar corredor demostrado de ubicación genérica y distinguir actividad compatible de un proceso/fábrica supuesto; verificar soporte y preguntas condicionales antes de ampliar automatización. Nada de esto se ajustará con los conjuntos retenidos. Factorial continúa aplazado.
