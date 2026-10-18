# Revisión relevante y atención de compras

## Resultado y recomendación

**Candidata review-1.1.0, sobre las predicciones congeladas de link-3.0.0-dev.** Revisión23→18de30training; cobertura automática23,3%→40%; errores entre automáticos0/7→0/12. Cinco automatizaciones correctas adicionales, tres de riesgo y urgencia positivos. Los cinco casos con errores conocidos siguen revisados. Ninguna probabilidad, predicción, prioridad, umbral ni dato del catálogo cambia.

Recomendación: **adoptar1.1 para el candidato de desarrollo**. No sustituir1.0.0default ni aplicar silenciosamente aRSS/2.2: faltan integración operativa del candidato y evidencia fuera de esta muestra inspeccionada. Las mejoras de representación/comparación sí se publican; abrirModelo no infiere ni cambia noticias históricas. A06 continúa abierto; S003 mantiene provincia desconocida.

## Qué provoca las23revisiones

|Causa|Noticias afectadas|Detalles bloqueantes|
|---|---:|---:|
|Asociación, inclusión o exclusión|15|48|
|Riesgo, ambigüedad o soporte|15|35|
|Urgencia ambigua|5|7|
|Severidad para prioridad|3|3|
|Estado de impacto|2|4|
|Datos ausentes del catálogo|0|0|
|Solo campos auxiliares|0|0|

Las causas se solapan. Hay40bloqueos sobre descartados, incluida la omisión real del servicio marítimo: no se eliminan en bloque. Los86detalles ya auxiliares/no bloqueantes permanecen visibles: categoría/evento, selección difusa de citas y campos irrelevantes para una decisión concreta.

Las tres dudas de severidad afectan prioridad/orden de atención, sin invalidar por sí solas riesgo o urgencia respaldados independientemente. Quedan en priority_requires_review y advertencias locales. Un inventario ausente seguirá desconocido y señalado, nunca cero ni buffer inventado. No había inventario ausente bloqueante en estas30filas; se cubre mediante un control sintético.

Impacto activo/resuelto, riesgo, urgencia y alcance inciertos sí pueden cambiar decisiones, recuperación o sonido. Los detalles por cada noticia, referencias, omisiones, respuestas y motivos exactos están exclusivamente en reports/private/REVISION_23_DIAGNOSTICO.md, review-policy-diagnosis.json y review-policy-before-after.json, fuera deGit/Docker/APIpública.

## Ensayos separados por hipótesis

|Ensayo|Revisión|Cobertura automática|Errores automáticos|Riesgos positivos automáticos|
|---|---:|---:|---:|---:|
|3.0original|23/30|7/30(23,3%)|0/7|0|
|Solo política, sin llamadas|23/30|7/30(23,3%)|0/7|0|
|1.0: soporte de decisión|22/30|8/30(26,7%)|0/8|0|
|1.1: soporte factual|18/30|12/30(40%)|0/12|3|

1. Aislamiento offline: localizar prioridad no libera ningún caso completo; todos tienen otro bloqueo relevante. Cero llamadas.
2. Soporte1.0: inclusión/exclusión y riesgo según polaridad predicha, con Noul>0,65 y cita válida. Cita sola no prueba asociación; riesgo condicionado tampoco. Añade soporte de urgencia.35HTTP200/0reintentos. Libera un negativo correcto. Exigir al texto sustentar coordinación del comprador bloquea incluso noticias con evacuación o cierre: el consejo no suele aparecer literalmente.
3. Hechos1.1: verifica la base factual de la regla de urgencia (cierre grave, evacuación, prohibición o recall frente a interrupción limitada/amenaza lenta). Para excluir: tema claramente no operativo, soporte factual y cita, identidad y vínculo finales<0,35. Baja inclusión sola no basta.29HTTP200nuevos; reutiliza35respuestas previas y todas lasA/B. No vuelve a pedir respuestas válidas ni vota entreJEV.

Congelaciones previas: review-support-freeze.json y review-facts-freeze.json. No se han modificado preguntas para mejorar resultados después de cada congelación. Los payloads, respuestas, modelo, uso y duraciones constan en informes privados/ledgerPostgreSQL.

## Predicciones y regresiones

En todos los estadios, incluyendo revisadas:

|Salida|TP/FP/FN|Precisión|Recall|F1|
|---|---:|---:|---:|---:|
|Riesgo|11/0/3|1|0,786|0,880|
|Urgencia|5/1/0|0,833|1|0,909|
|Proveedores|21/2/1|0,913|0,955|0,933|

Conjuntos exactos28/30. No regresiones de clasificación; los cinco casos erróneos permanecen revisados. Causas finales: asociación14noticias/44detalles, riesgo11/29, urgencia8/16, impacto2/4. Las nuevas comprobaciones de urgencia pueden mantener bloqueos aunque resuelvan otra duda.36detalles sobre descartados siguen bloqueando.

Cinco negativos aparentemente no operativos conservan revisión por discrepancia entreChoice de tema yNoul de soporte. Son oportunidad para mejorar representación, no justificación para rebajar umbrales. Otros pendientes sí tienen probabilidades fronterizas o datos operativos ausentes. Doce automáticos sin error no garantizan precisión de producción ni constituyen evaluación independiente.

## Sonido y acción: ejes distintos

- needs_review indica incertidumbre decisiva; human_attention distingue verificar, contacto inmediato y seguimiento. Urgente no significa análisis incierto.
- Severidad/duración/buffer inciertos siguen junto a la prioridad; no vetan una urgencia suficientemente respaldada por separado.
- Elegibilidad por proveedor/incidente: estadoactivo, sin incertidumbre decisiva y vínculo/riesgo/urgencia≥0,8, como antes. Otro proveedor incierto no silencia al sustentado. Monitoring, recuperación y ambigüedad relevante no suenan.
- Ninguno de los tres urgentes automáticos de training alcanza todos los0,8: no se fuerza sonido. El control sintético urgente sí cumple probabilidades y soporteJEV, aun con severidad incierta.
- Seis controles pasan: urgente+severidad, macroirrelevante, ruta desconocida, falso negativo parcial, urgencia fronteriza y positivo nombrado. Las bases sonMOCKidentificadas y solo soporte esJEVreal; no son precisión del clasificador completo.
- PostgreSQL sintético recorre reconcile con dos incidentes/avisos: uno elegible y otro silenciado. Navegador prueba mismo sondeo, gesto, una emisión y no repetición. No es audibilidad física: A14conserva confirmación previa ordenador/Firefox, alertaQAautomática y audio.ts sin cambios.

## Consumo y alcance

64HTTPnuevos(35+29), todos200,0reintentos; contador531→595, límite compartido126 sin reiniciar. UsoAPI:135374tokensentrada/11584salida. Suma duraciónHTTP19,864s: no es tiempo de lote niA20.35respuestas previas reutilizadas; cachehits HTTP de los payloads nuevos0. A/B de36casos guardadas;6controles tienen bases sintéticas explícitas. No se presupone coste monetario o saldo.

Validation retrospectiva, test/LiveDay/answerkey intactos. Factorial aplazado; RSSperiódico de pago desactivado. A20 sigue histórico de1.0.0/b4d697b,14filas/7,888s/23nuevas/0caché; no certifica el candidato con verificaciones adicionales.
