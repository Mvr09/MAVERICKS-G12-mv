# Geografía aislada: propuesta y resultado

Se preparó geo-1.0.1 como sucesor mínimo del perfil estable: mismos cuarentaNoul, mismas preguntas/puertas de riesgo y urgencia, misma política. Solo se añaden los hechos geográficos versionados con procedencia al estado A/B; una ubicación multirregión relevante conserva revisión y nota de provincia operativa desconocida. No se copia selección amplia/B/revisión de2.2.0. Preguntas originales verificadas por igualdad exacta.

## Desarrollo y regresiones

30training con baseline a igual extractor de duración y seis sintéticos en ambos perfiles. Respuestas anteriores reutilizadas únicamente si el payload efectivo coincide; una B de baseline con candidatos nuevos requirió una petición. No se ajustaron preguntas tras ver resultados. La fuente candidata quedó congelada antes de la única comparación retrospectiva ya inspeccionada. Test/LiveDay no participaron en este desarrollo.

| Medida de training | Original1.0.0 | Geografía aislada |
|---|---:|---:|
| Asociaciones correctas |13|11|
| Asociaciones falsas |1|0|
| Asociaciones omitidas |9|11|
| Riesgos omitidos |4|8|
| Urgencias omitidas |0|1|
| Urgencias falsas |3|0|
| Conjuntos exactos |25/30|24/30|

**Cero asociaciones correctas recuperadas, dos correctas perdidas, una falsa eliminada y ninguna falsa añadida.** Las mejoras de urgencia no compensan perder riesgos/asociaciones: **la propuesta no se activa como estable**. Predeterminado1.0.0 y experimental2.2.0 conservados. El perfil geográfico queda disponible para comprobaciones internas, no en las opciones de análisis públicas del presentador.

Sintéticos: el original conserva los tres proveedores del evento multiubicación; la variante pierde uno. Ambos omiten el proveedor de la interrupción parcial. Los negativos siguen sin asociaciones. La variante mantiene la ciudad ambigua sin provincia como posible exposición pendiente de revisión. Estos resultados son desarrollo, no una nueva estimación independiente de precisión.

## Qué decisión falla con los datos disponibles

En la comparación retrospectiva, la ubicación única enriquecida sí llega al estado, pero su Noul inicial de vínculo sigue por debajo de review_low: no pasa a B. **El dato geográfico aislado no basta para que la pregunta original interprete la exposición operativa.** Esto es distinto del proveedor cuya provincia falta. No se fuerza la asociación con la etiqueta esperada, no se usa riesgo condicionado para vincular y no se inventa la provincia.

La provincia de S003 continúa desconocida (Taizhou: Jiangsu/Zhejiang). Puede existir exposición potencial si su operación está en la zona afectada, pero el gazetteer no verifica esa sede. Detalle de la única comparación retrospectiva y probabilidades únicamente en reports/private/geo-regressions.json y stable-geography-results.json. A06 conserva su fallo conocido; capacidad funcional de múltiples asociaciones comprobada no equivale a acierto del modelo en ese caso.

## Consumo

62HTTP200, sin reintentos, dentro del techo438;44respuestas de etapa reutilizadas. Contador local253→315, sin reiniciar presupuestos previos. No se usa el remanente12/36 del ensayo de duración para estos artículos. No se ejecutó el factorial ni se activó RSS periódico de pago. El siguiente ensayo A20 es una única ejecución final de14filas con el estable conservado1.0.0 y el extractor actual, después de congelar el código de entrega; no prueba precisión ni alimenta correcciones.
