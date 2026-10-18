# Propuesta de vínculo y revisión · link-2.2.0

## Estado

Perfil experimental seleccionable, **1.0.0 permanece predeterminado**. Preguntas originales y política1.0.0 intactas. Ninguna excepción por News_ID. Desarrollo con30noticias training y sintéticos; perfil congelado antes de consultar resultados nuevos de validation. Test/LiveDay no se ejecutaron. Los datos de Railway no se reanalizaron automáticamente.

## Cambio general

1. Recuperación A con40Noul y pistas de nombre/geografía; una pista solo añade candidatura.
2. Confirmación B independiente de A: identidad, compatibilidad de área y compatibilidad operativa. Exposición=min(área,operación); vínculo=max(identidad,exposición). El riesgo condicionado no participa en esas composiciones. Son indicadores conservadores, no probabilidades calibradas ni supuestos de independencia.
3. Juicios distintos de riesgo y urgencia. La urgencia se refiere a coordinación inmediata ante una amenaza grave; no presupone stockout ni convierte automáticamente una interrupción regional en urgente.
4. Soporte de asociación/exclusión y de decisión de riesgo separado de selección de una cita. Una elección difusa entre varias citas válidas se muestra como observación; no se ignora la falta de soporte. Severidad, impacto y datos de cobertura siguen siendo relevantes para un riesgo asociado.
5. Revisión por campo y relevancia, sin propagar una categoría global incierta a cada proveedor. Incertidumbre de asociación o evidencia insuficiente siguen requiriendo revisión, incluidos candidatos no aceptados cuando su exclusión no está respaldada.

## Geografía y procedencia

36pares ciudad-país para40proveedores; no había regiones ni alias en el catálogo/payload original. Snapshot GeoNamesCCBY4.0 con fecha, hashes y URL por lugar, construido desde cities15000/admin1CodesASCII/countryInfo. No verifica empresas ni inventa plantas. Taizhou y Lancaster tienen alternativas de distintas regiones; Shanghai y Kaohsiung incluyen alias de distritos. Los lugares no se eligen por población ni por respuesta esperada.

Documentación primaria: [GeoNames](https://download.geonames.org/export/dump/readme.txt), [preguntas atómicas TypeSafe](https://docs.typesafe.ai/introduction), [contexto relevante y límites de Jev](https://docs.typesafe.ai/model-jaggedness/jev-1.13). Solo se envían alternativas de lugar/región y alias que coinciden con la noticia; snapshot completo auditable fuera del prompt.

## Training: comparación de desarrollo, no evaluación independiente

Mismos30artículos,14riesgos y5urgentes de referencia. Métricas incluyen predicciones en revisión, no solo el subconjunto automático.

| Medida | 1.0.0 | link-2.2.0 |
|---|---:|---:|
| Riesgo TP / FP / FN | 10 / 0 / 4 | 12 / 0 / 2 |
| F1 de riesgo | 0,8333 | 0,9231 |
| Urgencia TP / FP / FN | 5 / 3 / 0 | 5 / 0 / 0 |
| F1 de urgencia | 0,7692 | 1,0000 |
| Asociaciones TP / FP / FN | 13 / 1 / 9 | 17 / 0 / 5 |
| F1 de proveedores | 0,7222 | 0,8718 |
| Conjuntos exactos | 25/30 | 26/30 |
| Noticias en revisión | 16/30 | 22/30 |

Cambios por noticia:3riesgos corregidos y1riesgo previamente acertado que pasa a omitirse;3urgencias falsas eliminadas, sin nuevas omisiones de urgencia. Se recuperan4asociaciones correctas y se elimina1incorrecta; no se pierde ninguna asociación que antes fuera correcta. Persisten5asociaciones omitidas y2riesgos omitidos. La regresión de riesgo se conserva y se describe por noticia en el informe privado.

Borradores previos conservados:2.0 tenía F1riesgo0,6667/proveedores0,6250/urgencia0,5714 y30revisiones;2.1 mejoró proveedores a0,9268 pero omitió3urgentes. Se descartaron como propuesta final. No se presentan como evaluaciones independientes ni se ocultan ensayos fallidos.

## Validación ya inspeccionada: comparación retrospectiva

Referencia histórica almacenada de Railway, sin volver a llamar a v1. Propuesta congelada antes de sus nuevas llamadas. Diez noticias; no ajustar después de ver estos resultados.

| Medida | 1.0.0 histórica | link-2.2.0 |
|---|---:|---:|
| Riesgo TP / FP / FN | 3 / 0 / 2 | 4 / 0 / 1 |
| F1 de riesgo | 0,7500 | 0,8889 |
| Urgencia TP / FP / FN | 2 / 0 / 0 | 2 / 1 / 0 |
| F1 de urgencia | 1,0000 | 0,8000 |
| Asociaciones TP / FP / FN | 7 / 0 / 3 | 8 / 0 / 2 |
| F1 de proveedores | 0,8235 | 0,8889 |
| Conjuntos exactos | 8/10 | 8/10 |
| Noticias en revisión | 8/10 | 9/10 |

Hay1urgencia falsa nueva, señalada para revisión. Recuperar una asociación no prueba urgencia ni garantiza recuperar todas las asociaciones. La ambigüedad de una ciudad puede requerir completar el catálogo con procedencia, no deducir la provincia a partir de una etiqueta esperada. Detalle con referencias solo en `reports/private/link-retrospective-comparison.json`.

## Seis casos sintéticos con JEV real tras congelar

Cinco cumplen las expectativas declaradas: varias ubicaciones, alias Łódź/Bangalore con noticias irrelevantes, ambigüedad de ciudad que debe revisarse y homónimo en ciudad coincidente. Falla el caso de interrupción parcial: no confirma la asociación y omite el riesgo, aunque riesgo condicionado supera el umbral. Queda en revisión y no se vuelve urgente. No se ajustó el perfil después. Estos casos comprueban conductas concretas, no estiman precisión general.

## Pruebas y consumo

-120tests backend/integración con mocks pasan;13E2E dirigidos pasan a360/390/768/1440. BuildTS/Vite pasa. Snapshot/configuración incluidos en Docker y paquete; sin datasets originales ni secretos.
-241peticiones nuevas registradas:210en training(incluidos borradores),19en retrospectiva y12en sintéticos.237HTTP200 y4HTTP400. Modelo validadojev-1.13.0. Intentos, duración y uso reportado por API quedan en informes privados; uso agregado en link-v2-summary.json. No se estima saldo ni coste.
-Los primeros400detuvieron el ensayo. La causa de tamaño/contexto fue la hipótesis principal; el cuerpo original no se conservó y no se afirma un código de error desconocido. Compactar el estado permitió el control autenticado y continuar. Intentos/consumo no se reiniciaron; se conserva el diagnóstico. El cliente guarda en adelante solo códigos de error reconocidos, sin mensajes que puedan repetir credenciales o entradas.
-Caché/reanudación conservaron las30predicciones de referencia y los resultados completados; no se repitieron para cada borrador. El congelado se conserva en link-v2-freeze.json. No se alteró la política para mejorar métricas.

## Límite de la propuesta

No se promueve a predeterminado: mejora cobertura/riesgo en desarrollo, pero aumenta revisión, presenta una regresión de riesgo en training y una de urgencia en retrospectiva, y falla una prueba sintética de interrupción parcial. Hace falta una evaluación independiente nueva para estimar generalización; repetir esta validación no la crea. No se afirma mejora de RSS: mantiene su perfil separado y el pago periódico desactivado.
