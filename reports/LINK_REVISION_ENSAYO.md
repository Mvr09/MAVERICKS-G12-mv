# Diagnóstico de revisión y ensayo propuesto

**Estado: ensayo factorial aplazado por indicación del usuario.** La auditoría acotada y la comprobación de duraciones vigente están en [AUDITORIA_SOPORTE.md](AUDITORIA_SOPORTE.md). El diseño siguiente se conserva como propuesta histórica, sin ejecución.

## Estado y alcance

1.0.0 sigue predeterminado y link-2.2.0 experimental. Este diagnóstico reutiliza los 30 resultados actuales de training, los seis sintéticos y sus respuestas A/B cacheadas. No cambia preguntas, umbrales, catálogo, código ni predicciones. Cero llamadas nuevas a JEV; contador local conservado en 241. Validation no interviene en este diagnóstico ni en la selección del ensayo; sigue siendo una comparación retrospectiva. Test/LiveDay no se consultaron. RSS periódico de pago continúa desactivado.

Los detalles por noticia, referencias, respuestas y proveedores omitidos están en `reports/private/LINK_REVISION_DIAGNOSTICO.md`, `link-review-cause-breakdown.json`, `link-support-audit.json` y `link-cached-scope-diagnosis.json`, excluidos de Git y Docker.

## 1. Qué provoca la revisión

Conteos de **noticias distintas**, con solapamiento entre causas. No deben sumarse las filas para obtener el total.

| Causa bloqueante | Training (30; 22 en revisión) | Sintéticos (6; 6 en revisión) |
|---|---:|---:|
| Asociación o soporte de asociación/exclusión | 18 | 6 |
| Riesgo ambiguo o soporte de riesgo insuficiente | 14 | 1 |
| Urgencia ambigua | 4 | 0 |
| Severidad incierta | 3 | 0 |
| Estado del impacto incierto/contradictorio | 6 | 0 |
| Datos de catálogo/cobertura ausentes | 0 | 0 |
| Duración/prioridad, otros bloqueos | 0 | 0 |
| Observaciones auxiliares, **no bloqueantes** | 21 | 6 |

Training: 18 noticias tienen `association_support_insufficient` (46 evaluaciones de proveedor), cuatro tienen vínculo ambiguo (siete evaluaciones); 14 tienen soporte de riesgo insuficiente (16 evaluaciones), seis riesgo ambiguo, cuatro urgencia ambigua (seis evaluaciones), tres severidad incierta y seis impacto incierto; una de estas últimas también contiene contradicción riesgo/impacto. Todas las 46 evaluaciones con soporte de asociación insuficiente tienen Noul de soporte ≤0,65; en 34 también se eligió cita `none`. Las 16 de soporte de riesgo tienen Noul ≤0,65; tres también carecen de cita. La elección difusa de citas no explica por sí sola estos bloqueos.

Las 22 se reconcilian así: 18 con bloqueo de asociación, más cuatro sin él pero con bloqueo de riesgo/impacto. Ocho se revisan exclusivamente por candidatos no aceptados: seis tienen salida negativa correcta y dos contienen omisiones reales de riesgo/proveedores. No se pueden eliminar todos los bloqueos de candidatos descartados. Catorce noticias tienen algún bloqueo en un proveedor aceptado y doce en uno descartado; hay solapamiento. En 18 de las 22 coinciden riesgo, urgencia y conjunto de proveedores con la referencia de training: acertar esas etiquetas no demuestra que el soporte o la prioridad sean fiables.

Las observaciones auxiliares aparecen en 21 noticias de training, incluidas dos que terminan correctamente sin revisión. Son confidencias de categoría/estado global, selección de citas, geografía sin resolver o campos de proveedores sin riesgo. No son el origen de las 22 revisiones. Una incertidumbre de impacto o severidad sí es bloqueante cuando afecta a un riesgo asociado.

### Los seis sintéticos

- **Varias ubicaciones:** detecta las tres asociaciones y riesgo/urgencia esperados. Revisa soporte de asociación (0,47/0,40/0,42) y de riesgo (0,34/0,32/0,35), aunque selecciona citas. Hay desacuerdo entre las decisiones y sus preguntas de soporte; no es un fallo de UI ni de selección de candidatos.
- **Festival en Łódź:** salida negativa correcta; soporte de exclusión 0,34, con cita seleccionada. Revisión de asociación del candidato geográfico descartado.
- **Exposición universitaria en Bangalore:** negativa correcta; soporte de exclusión 0,48, con cita. Mismo mecanismo.
- **Interrupción parcial en Hangzhou:** omite asociación/riesgo; revisa vínculo ambiguo y soporte de asociación del objetivo, más soporte de exclusión de otro candidato regional.
- **Taizhou ambiguo:** mantiene revisión por asociación/exclusión insuficiente. Esa abstención es apropiada: falta saber en cuál de las ciudades está el proveedor. No hay un conjunto de proveedores de referencia impuesto para este caso.
- **Homónimo financiero en Basel:** negativa correcta; soporte de exclusión 0,55 y cita `none`. Revisar si el criterio de evidencia admite probar una exclusión, antes de considerarlo resuelto.

Los seis tienen observaciones auxiliares, pero ninguna los manda sola a revisión. Los tres negativos inocuos deberían poder resolverse automáticamente **si** las exclusiones quedan respaldadas; sus salidas binarias correctas no autorizan a saltarse ese requisito.

## 2. Omisión de interrupción parcial

Noticia sintética: fábricas de Hangzhou reducen consumo eléctrico un 20 % durante dos días y mantienen producción reducida. Catálogo: proveedor de prospectos, categoría embalaje secundario, ciudad Hangzhou; no describe expresamente la instalación ni su proceso de fabricación.

| Señal almacenada | Valor |
|---|---:|
| Candidatura A | 0,72 |
| Amenaza del artículo | 0,81 |
| Identidad B | 0,13 |
| Área B | 0,86 |
| Compatibilidad operativa B | 0,47 |
| Soporte de asociación | 0,36 |
| Riesgo condicionado / soporte de riesgo | 0,59 / 0,55 |
| Urgencia | 0,20 |
| Confianza del impacto activo | 0,21 |

La ciudad y Zhejiang están presentes y correctamente enriquecidos en el payload efectivo. El proveedor llega a B: no falla la recuperación ni falta el alias. El cuello de botella observado es **interpretar la compatibilidad operativa** con un catálogo que describe un producto, no el tipo de instalación. La composición aplica exactamente lo previsto: `exposición=min(0,86;0,47)=0,47`, `vínculo=max(0,13;0,47)=0,47`. El riesgo de 0,59 no puede confirmar esa asociación. Esto demuestra la ruta de la omisión, pero una sola respuesta no prueba si la causa semántica es falta de datos del negocio o interpretación de JEV. No hay evidencia de un error aritmético.

Falta además una extracción: `durations()` solo reconoce cifras y no convierte «two days»; por ello B recibe únicamente duración desconocida, aunque el texto original completo sí se envía. En este caso no causa el vínculo bajo ni un bloqueo por datos ausentes: el lead time permite calcular cobertura. Se investigaría en un ensayo separado para no mezclar factores.

Incluso si se confirmara el vínculo conservando las demás respuestas, el caso seguiría en revisión por riesgo 0,59, soporte 0,55 e impacto con confianza 0,21. Corregir la asociación no justifica marcarlo como resuelto ni urgente. La expectativa de desarrollo es exposición potencial de una operación compatible, riesgo y **no urgencia**, sin afirmar daño individual ni pérdida de stock. Hace falta confirmar el proceso industrial para distinguir esa exposición potencial de afectación directa.

## 3. Ensayo acotado propuesto, todavía no ejecutado

### Diseño previamente fijado

Ensayo factorial 2×2 sobre **12 noticias de training y los seis sintéticos existentes**, con selección congelada antes de ejecutar. Training cubre identidad explícita, varias ubicaciones, interrupción limitada, logística, omisiones actuales y negativos por geografía/homónimos. La lista exacta queda en el informe privado; no usa validation. Es una muestra deliberada de diagnóstico, no una estimación independiente de precisión.

| Brazo | Factor vínculo/geografía L | Criterio urgencia U |
|---|---|---|
| A | L0: vínculo de A y catálogo original | U0: pregunta 1.0.0 |
| B | L1: geografía verificable y confirmación independiente en B | U0: pregunta 1.0.0 |
| C | L0 | U1: criterio de coordinación inmediata de 2.2.0 |
| D | L1 | U1 |

A/B a U0 constante aíslan el paquete vínculo/geografía. C/D comprueban ese efecto bajo U1. A/C y B/D aíslan urgencia; se informa también su interacción. El factor L agrupa geografía y confirmación, por lo que este ensayo no separa esos dos componentes entre sí.

Constantes: modelo jev-1.13.0, texto sin etiquetas, las 40 identidades, snapshot del catálogo/geografía, extractor de duración actual, umbrales, política de prioridad y criterio de riesgo **original 1.0.0**. El cambio de redacción de riesgo de 2.2.0 y la corrección de duración quedan fuera. Las mismas preguntas instrumentales de soporte y la misma política de revisión por campo se aplicarán a los cuatro brazos; se archivarán decisiones, soporte y citas en bruto. L0 se instrumenta para medir revisión comparable: **A no debe presentarse como una nueva ejecución idéntica del perfil de producción 1.0.0**. Ese perfil permanece intacto y sus resultados históricos se muestran aparte.

Comparar también, sin llamadas adicionales, identidad, área, operación y el mínimo final para distinguir el efecto de la composición. No sustituir el mínimo por riesgo ni cambiar la fórmula después de ver el resultado. Los cambios del estado común pueden afectar otras respuestas del modelo: publicar cualquier deriva en riesgo y proveedores entre U0/U1, no atribuirla automáticamente a una mejora semántica de urgencia.

**Techo: 18 entradas × 4 brazos × 2 etapas = 144 peticiones iniciales; hasta 432 HTTP incluyendo un máximo de tres intentos por etapa.** Se reutilizará una caché solo si coinciden payload efectivo, modelo y versión experimental; etapas A idénticas entre U0/U1 reducen consumo, sin reiniciar contadores. No repetir respuestas válidas para elegir una favorable. Parar ante 401 o error de contrato antes de insistir. Contabilizar intentos, errores, duración y uso real; no estimar coste monetario sin tarifa/uso verificable. Esta propuesta no ejecuta ese lote ni activa RSS de pago.

### Expectativas de revisión y criterios, antes de ejecutar

1. Negativos inocuos: sin riesgo, sin urgencia y sin asociación. Solo pueden salir de revisión si hay exclusión respaldada y sin candidato relevante sin resolver; no basta con obtener un Noul bajo de vínculo.
2. Varias ubicaciones: conservar todas las asociaciones correctas, riesgo y urgencia esperados. Revisión cuando falte soporte; no forzar estado finalizado por acertar las etiquetas.
3. Interrupción parcial: objetivo de vínculo y riesgo respaldados, sin urgencia; si persiste ambigüedad en asociación, riesgo o impacto, mantener revisión y explicarla. No exigir una caída de revisión para considerar útil el diagnóstico.
4. Ciudad ambigua: revisión obligatoria mientras no esté confirmado el lugar del proveedor; ninguna asociación final confirmada por escoger la alternativa que encaja con la noticia.
5. Auxiliares: una categoría o cita difusa nunca bloquea sola; impacto, severidad o ausencia de datos operativos siguen bloqueando cuando son relevantes.
6. Evaluación de riesgo/proveedores/urgencia sobre **todas** las noticias, incluidas las revisadas. Informar TP/FP/FN, F1, conjuntos exactos y diferencias por noticia; aparte, cobertura automática, errores en casos automáticos, causas de revisión y soporte de exclusión. No usar solo F1 agregado o tasa de revisión.

**Para avanzar a candidato congelado:** ninguna asociación correcta del control perdida, ningún proveedor falso adicional, ningún FN de riesgo o urgencia nuevo y ninguna urgencia falsa adicional en comparaciones emparejadas; cumplir las expectativas sintéticas y de soporte, explicar todas las regresiones y no ocultarlas detrás de revisión. Si falla un criterio, conservar el experimental y el predeterminado actual. Los resultados mixtos actuales no satisfacen una promoción.

**Para promover a predeterminado:** además, comprobar el training completo con la versión elegida ya congelada y superar las mismas guardias de regresión; realizar en su fase autorizada una evaluación final con datos retenidos no usados para desarrollar, exportación y ensayo operativo. Fijar el protocolo/muestra antes de abrirlos y no ajustar con sus resultados. La validation inspeccionada solo se informa retrospectivamente, nunca como prueba independiente. Este ensayo de desarrollo no basta por sí solo para promover.

## 4. Catálogo: qué confirmar y qué enriquecer

40 proveedores; 36 pares ciudad-país. Ciudad, país, categoría y material están presentes en todos. No hay campos de instalación industrial, coordenadas verificadas del proveedor, huella operativa, proceso, modo/ruta de transporte ni provincia aportada por el propietario.

| Dato | Acción y procedencia admisible |
|---|---|
| Ciudad → región, país ISO, nombres locales y transliteraciones | Enriquecer con gazetteer verificable (snapshot GeoNames ya disponible), URL, fecha y versión; conservar alternativas. Es geografía de lugares, no prueba de plantas. |
| Taizhou y Lancaster | El propietario debe confirmar provincia/estado o dirección. Hay dos candidatos multirregión y cuatro respectivamente. Un gazetteer no puede escoger la sede del proveedor ficticio. |
| Shanghai y Kaohsiung | Revisar precisión ciudad/distrito si importa el alcance local; los candidatos actuales comparten región administrativa, pero no prueban dirección de planta. |
| Tipo de instalación, fabricación propia/subcontratada, proceso eléctrico y exposición regional | Confirmar con propietario del catálogo; categoría/material no certifican una fábrica ni su dependencia de energía. Si se añaden reglas taxonómicas, marcarlas como hipótesis o hechos confirmados, nunca hechos inventados por proveedor. |
| Modo y rutas logísticas, puertos/corredores usados | Confirmación operativa. Fuentes públicas prueban que una ruta/puerto existe, no que este proveedor la utilice. |
| Lead time y stock | 1 lead time vacío en Services y 6 stocks vacíos en Logistics/Services. No son seis stocks físicos desconocidos: stock no aplicable según política. Confirmar el lead time solo si ese servicio lo requiere; no reemplazar vacíos por cero. No hay stock físico vacío en este catálogo. |
| Alternativos | 14 proveedores y 10 materiales sin alternativo declarado. Ausencia no demuestra inexistencia o capacidad. Stock/capacidad/plazo del alternativo requieren confirmación. |
| Materiales/productos | 20 materiales; 10 de las 40 identidades no aparecen como primario/alternativo en Materials. Confirmar si faltan relaciones o no aplican; mantener «Productos no mapeados» donde corresponda. |
| Criticidad, fuente única y cuota | Presentes en los 40, pero no se verifican con un gazetteer. Conservar la procedencia del catálogo y solicitar al propietario correcciones si faltan o quedan obsoletos. |

No investigar empresas reales para completar datos empresariales de una cartera ficticia. Fuentes geográficas nuevas solo si una pregunta concreta las necesita; este diagnóstico no hizo consultas externas nuevas.

## Evidencia y límite

Comprobación de consistencia de informes y cachés en PostgreSQL local mediante transacciones de solo lectura. No se ejecutaron pruebas de precisión nuevas, tests de UI ni despliegue: no hay cambios funcionales. Los 5/6 sintéticos acertados se refieren a sus expectativas originales (el ambiguo comprueba revisión), no a seis decisiones plenamente verificadas ni a precisión independiente.
