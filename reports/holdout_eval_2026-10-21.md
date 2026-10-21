# Holdout independiente · evaluación del perfil desplegado (2026-10-21)

> **Muestra pequeña (30 noticias ficticias generadas por IA).** Un error mueve la precisión/recall varios puntos; las cifras orientan, no certifican. Ver construcción y límites en `docs/HOLDOUT.md`.

- Web: https://mavericks-g12-mv-production.up.railway.app · revisión `21c92ef` · esquema 0010
- Perfil por defecto: `radar-1.0.0-candidate` · preguntas `decision-3.4.2` · JEV `jev-1.13.0`
- Lote importado `b50f38db-8042-4022-94a5-388d6604245c` · 30/30 analizadas · errores 0
- Tiempo de lote (servidor): n/d s · cliente, importación→fin: 13.6 s · peticiones 95 (HTTP 200: 95) · tokens entrada 845944 / salida 62536 · coste aprox. 0.0358 $ (tasa histórica 0.03941248835 $/M, no tarifa oficial)
- Limpieza: deleted · cifras públicas de Ejercicio tras limpiar: idénticas a las previas

## Resultados

| Pregunta | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Is_Risk (n=30) | 17 | 0 | 0 | 13 | 1.00 | 1.00 | 1.00 |
| Urgent (n=30) | 8 | 1 | 0 | 21 | 0.89 | 1.00 | 0.94 |
| Proveedores (pares, 20 esperados) | 20 | 1 | 0 | – | 0.95 | 1.00 | 0.98 |

Conjuntos de proveedores exactos: **29/30** · filas exactas (las tres respuestas): **28/30**.

## Por tipo de caso

| case_type | n | Riesgo ok | Urgencia ok | Proveedores exactos | Filas exactas | Errores |
|---|---|---|---|---|---|---|
| direct | 8 | 8/8 | 8/8 | 8/8 | 8/8 | – |
| location_trap | 3 | 3/3 | 3/3 | 3/3 | 3/3 | – |
| name_trap | 4 | 4/4 | 4/4 | 4/4 | 4/4 | – |
| noise | 3 | 3/3 | 3/3 | 2/3 | 2/3 | H015 |
| regional | 6 | 6/6 | 5/6 | 6/6 | 5/6 | H016 |
| strategic | 3 | 3/3 | 3/3 | 3/3 | 3/3 | – |
| supplier_positive | 3 | 3/3 | 3/3 | 3/3 | 3/3 | – |

## Automáticas vs revisión

| Estado mostrado | n | Filas exactas | Errores |
|---|---|---|---|
| Automática | 14 | 14/14 | – |
| Duda del modelo resuelta por alcance | 0 | 0/0 | – |
| Revisión humana | 16 | 14/16 | H015, H016 |

## Errores fila a fila

| News_ID | case_type | Esperado (riesgo/urgencia/proveedores) | Predicho | Estado |
|---|---|---|---|---|
| H015 | noise | N/N/– | N/N/S015 | review |
| H016 | regional | Y/N/S033 | Y/Y/S033 | review |

## Límites

- Noticias y etiquetas generadas por IA a partir del README y el catálogo; sin revisión humana independiente.
- 30 casos inequívocos por diseño: no mide casos dudosos ni ruido real de RSS; la distribución no es la del mundo real.
- Una sola ejecución (sin repetir para medir variabilidad del modelo).
- Las métricas se calculan sobre la exportación oficial del lote (columnas Is_Risk, Urgent, Affected_Supplier_IDs).
