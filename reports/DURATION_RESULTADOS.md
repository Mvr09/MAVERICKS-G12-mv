# Comprobación dirigida de duración · resultados

Seis sintéticos según el plan congelado. JEV real desde desarrollo local, modelo jev-1.13.0, perfil experimental link-2.2.0; 1.0.0 sigue predeterminado. Preguntas y umbrales intactos. No se consultaron validation/test/LiveDay ni se ejecutó el factorial.

| Caso | Fragmento conservado | Días | Tipo | Riesgo | Urgencia | Estado |
|---|---|---:|---|---|---|---|
| en_words | two days | 2 | Exacta | Sí | No | Revisión |
| en_digits | 2 days | 2 | Exacta | Sí | No | Revisión |
| es_words | dos días | 2 | Exacta | No | No | Revisión |
| es_digits | 2 días | 2 | Exacta | No | No | Revisión |
| en_min_words | at least two days | 2 | Límite inferior | Sí | No | Revisión |
| en_min_digits | at least 2 days | 2 | Límite inferior | Sí | No | Revisión |

**6/6 pasan las expectativas de duración.** Todas las respuestas seleccionan d1 para S024: dos días, cita exacta y conservación del límite inferior. El texto y la unidad originales se preservan en el candidato; la unidad canónica es días.

**Consumo:** 12 HTTP200, 0 reintentos, de un máximo de36; contador local total241→253. Primera ejecución 5.598s, medidos localmente. Reanudación reutiliza seis resultados ya válidos con0llamadas nuevas y conserva el contador12. Uso reportado: 193674 input_tokens y 10654 output_tokens; no se infiere coste monetario.

Los tres pares palabras/cifras coinciden en riesgo, urgencia y estado de revisión; sus motivos detallados y puntuaciones pueden diferir. Los seis permanecen en revisión y ninguno es urgente. Los casos españoles excluyen S024 por compatibilidad operativa insuficiente y quedan sin riesgo, mientras que los ingleses aceptan el vínculo y muestran riesgo: se conserva esa diferencia sin ajustar preguntas. Las confianzas de duración van de0,42 a0,64; elegir la duración correcta no elimina una revisión relevante por baja confianza.

Respecto al sintético parcial histórico, el nuevo caso inglés pasa de riesgoN aY y mantiene urgenciaN/revisión; el vínculo cambia de0,47 a0,51. El payload ahora contiene candidatos de duración, pero también difieren metadatos de la noticia y la ejecución: no es una ablación causal ni demuestra una mejora general del clasificador.

**Indefinidos:** comprobados offline (until further notice, indefinitely, por tiempo indefinido, varios días) sin inventar duración. Ninguno de los seis textos JEV autorizados es indefinido; no se presenta esa parte como ensayo autenticado.

Evidencia agregada: duration-directed-results.json. Respuestas, hashes completos del ensayo, intentos y uso por petición permanecen en reports/private/duration-directed-results.json y en la cola/contabilidad de la base local dedicada. No se publican referencias protegidas ni originales.
