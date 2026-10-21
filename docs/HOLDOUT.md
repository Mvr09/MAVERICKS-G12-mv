# Holdout independiente de noticias · 21 de octubre de 2026

`docs/HANDOFF_FINAL.md` reconoce que training y validation **no son validación independiente**: el equipo las ha leído y ha ajustado el perfil con ellas. Este holdout es un conjunto nuevo de 30 noticias etiquetadas para medir el perfil final desplegado (3.4.2 / revisión 1.3.1, `radar-1.0.0-candidate`) sin tocar código de la app.

| Archivo | Qué es |
|---|---|
| `inputs/supplier_holdout.xlsx` | Hoja `News_Test` con el formato de test: News_ID, Published_Date, Source, Headline, Summary, Is_Risk, Urgent, Affected_Supplier_IDs. Las tres últimas columnas van **vacías**, así que la app no recibe respuestas (el importador no crea `EvaluationLabel`). |
| `inputs/supplier_holdout_labels.json` | Respuestas aparte: News_ID, Is_Risk, Urgent, Affected_Supplier_IDs, case_type y explanation. |
| `scripts/build_holdout.py` | Genera los dos archivos anteriores y ejecuta las dos pasadas de etiquetado y las comprobaciones de no reutilización. Falla si algo no cuadra. |
| `scripts/evaluate_holdout.py` | Mide la web desplegada solo con la API HTTP y escribe `reports/holdout_eval_<fecha>.json` y `.md`. |

## Construcción

- 30 noticias ficticias en inglés, IDs `H001`–`H030`, fechadas entre el 7 y el 20 de octubre de 2026. Las fuentes son medios inventados.
- Solo se usan proveedores del catálogo de `supplier_training.xlsx` (hoja Suppliers, 40 proveedores).
- No se abrieron `inputs/supplier_test.xlsx`, `inputs/supplier_liveday.xlsx` ni ningún answer key.
- Las noticias de training/validation no se leyeron para escribir estas. El generador solo las compara por solapamiento de palabras y por las columnas de etiqueta (proveedor + Event_Type), sin imprimir textos.
- **Reescritura por solapamiento.** La primera versión coincidía con casos ya existentes en training/validation: el par proveedor + tipo de evento de la exportación de amoxicilina en India (S001/S002), la quiebra de S012, una catástrofe natural en S025 (el mismo huracán, incluso con el mismo nombre) y otra en S013. También coincidía con una trampa con «Atlas», una noticia sobre smartphones y otra sin proveedor afectado en Lodz. Se sustituyeron las 9 noticias por escenarios nuevos. El generador ahora falla si algún par (proveedor, tipo de evento) se repite o si el Jaccard de palabras con alguna noticia de training/validation llega a 0,20. Valor final: 0,159; el solapamiento que queda son nombres y ciudades del catálogo.

## Reparto

| case_type | n | Is_Risk | Urgent | Proveedores |
|---|---|---|---|---|
| direct: el proveedor aparece con su nombre exacto | 8 | Y | 5 Y / 3 N | el nombrado |
| regional: ciudad o región sin nombrar al proveedor | 6 | Y | 3 Y / 3 N | el de esa ciudad y país |
| strategic: riesgo a ≥ 12 meses | 3 | Y | N | el nombrado |
| supplier_positive: noticia positiva de un proveedor | 3 | N | N | el nombrado |
| name_trap: empresa con nombre parecido | 4 | N | N | – |
| location_trap: misma ciudad, otro país | 3 | N | N | – |
| noise: sin relación con el suministro | 3 | N | N | – |
| **Total** | **30** | **17 Y** | **8 Y** | **20 pares** |

Urgentes: H012 (S003), H017 (S025), H020 (S011), H021 (S008), H024 (S028), H025 (S012), H026 (S017) y H027 (S020). Cada noticia lleva su explicación en el JSON.

## Criterios de etiquetado

Se aplican los criterios del README de `supplier_training.xlsx`:

- **Is_Risk.** ¿Puede afectar al suministro de Helixa?
- **Urgent.** Solo puede ser Y si hay riesgo. Es Y cuando el evento puede parar o retrasar mucho y pronto a un proveedor, teniendo en cuenta su dependencia: fuente única, criticidad y cobertura de inventario. Los efectos menores, cortos o lentos quedan en N.
- **Affected_Supplier_IDs.** Vacío si no hay proveedor afectado.

Para que no haya casos discutibles, solo entran casos de los extremos:

- **Urgente.** Producción o envíos parados durante más días que la cobertura de inventario y sin alternativa aprobada sin afectar (todos los urgentes son de fuente única). Todos dicen la duración: por ejemplo, 10 semanas frente a 40 días de cobertura.
- **Riesgo no urgente.** Retrasos de 10 días como máximo, o cambios a 12 meses o más vista. No hay ningún caso «grave pero con alternativa», el único punto que el README deja a criterio.
- **Regional.** La noticia dice la ciudad y el país de un único proveedor del catálogo y que el cierre afecta a todas las fábricas de la zona.
- **Trampas.** El nombre o la ciudad coinciden en parte, pero el país o la actividad lo descartan sin ambigüedad.
- **Positivas.** Riesgo N con el ID del proveedor, como pide la tarea. Además no contienen palabras que la app usa para cerrar incidentes por «recuperación» (`app/incidents.py`).
- Se evitó la ubicación de S003 (Taizhou, A06 abierto). S003 solo aparece nombrado.

## Segunda pasada independiente

`build_holdout.py` vuelve a calcular cada etiqueta sin usar la de la primera pasada:

1. Detecta en el texto los nombres exactos del catálogo.
2. Detecta pares ciudad + país del catálogo.
3. Con los hechos que declara el texto (tipo de efecto y duración mínima), aplica las reglas anteriores con los datos del catálogo: alternativa y cobertura.
4. Comprueba que cada case_type tiene la forma esperada; por ejemplo, una trampa no puede tener proveedor.

Resultado: las 30 etiquetas coinciden en Is_Risk, Urgent y proveedores. Como prueba del propio control, se cambiaron una a una las 90 respuestas (30 × 3) y la segunda pasada detectó las 90.

## Medición sobre la web compartida

**Estado a 21/10: no ejecutada.** El script está listo, pero falta la contraseña de presentador. Para lanzarlo:

```powershell
$env:RADAR_URL = "https://mavericks-g12-mv-production.up.railway.app"
$env:RADAR_PASSWORD = "..."           # no se guarda en el repo
python scripts/evaluate_holdout.py --preflight   # solo comprobaciones, no importa nada
python scripts/evaluate_holdout.py               # importa, analiza, exporta, limpia e informa
```

Flujo (solo HTTP):

1. Inicia sesión como presentador.
2. `POST /api/imports` con el xlsx.
3. `POST /api/batches/{id}/analyze` sin cuerpo, es decir, con el perfil por defecto.
4. Espera con `GET /api/batches`.
5. Descarga `GET /api/batches/{id}/export.xlsx`; las métricas salen de esta exportación.
6. Lee `GET /api/articles?origin=batch:{id}` (automática o revisión) y `GET /api/batches/{id}/execution` (peticiones y tokens).
7. Limpia y compara.

El informe incluye:

- Riesgo y urgencia: TP/FP/FN/TN, precision, recall y F1.
- Proveedores: TP/FP/FN por par y conjuntos exactos.
- Desglose por case_type.
- Automáticas, dudas resueltas por alcance y revisión.
- Denominadores y advertencia de muestra pequeña.

### ¿Se puede borrar el lote y cambiaría lo que ven los compañeros?

Revisado en el código (`app/demo.py`, `app/incidents.py`, `app/views.py`, `app/final_model.py`, `app/model_metrics.py`, `app/campaigns.py`):

- **Sí se puede borrar.** `POST /api/demo/preview` con `{"selection":["batch:<id>"],"mode":"delete"}` y después `POST /api/demo/cleanup` con `LIMPIAR DEMO`. Se borran el lote, sus artículos, análisis, filas importadas, jobs y comparaciones. Los incidentes que solo tienen evidencia de este lote se borran con sus alertas. El script lo hace siempre al terminar, también si falla a medias.
- **Mientras el lote existe (unos minutos) sí se ve:** suma 30 noticias, alertas e incidentes al contexto **Ejercicio**, y sus jobs entran en la telemetría Railway de `/api/model/final`. Un presentador con el audio activado podría oír alertas.
- **Después de la limpieza vuelve a lo anterior:**
  - Resumen y Proveedores de Ejercicio.
  - Alertas.
  - `/api/model/final`. La calidad sale de la campaña congelada, que no se toca. La parte Railway sale de jobs, y estos se borran.
  - `/api/model/metrics`. Solo cuenta llamadas de artículos que siguen existiendo.
  - Comparador (`/api/campaigns`). Usa tablas propias que no se tocan.

  El script compara estas cifras antes y después y registra cualquier diferencia.
- **Se conserva por diseño:**
  - Las filas `ApiCall`.
  - El contador `requests_used` del presupuesto `manual-unlimited-20261017`.
  - El `used` del grant de test ilimitado.

  La app nunca los borra; es el consumo real de la ejecución.
- **Riesgos y protecciones:**
  1. Si una noticia del holdout se uniera a un incidente existente (mismo proveedor y tipo, ≤ 7 días y Jaccard ≥ 0,5 en `incidents.py`), la limpieza recrearía las alertas de ese incidente y borraría sus borradores. Protección: antes de importar, el script calcula ese solapamiento contra los incidentes actuales de Ejercicio y aborta si llega a 0,35. Después del análisis informa de cualquier incidente compartido.
  2. El esquema **0011** (planes de acción, PR #5, en `main` y aún sin desplegar) añade `action_plans` con clave foránea a incidentes, y la limpieza no los borra. Si un presentador abriera planes mientras existe el lote, el borrado podría fallar. Protección: el script solo importa si `/readyz` devuelve el esquema **0010**, el que está desplegado hoy (revisión 21c92ef). Con 0011 hay que revisar la limpieza antes.
  3. Si queda un lote a medias: `python scripts/evaluate_holdout.py --cleanup-batch <id>`.

## Límites

- **Generado por IA.** Noticias y etiquetas las escribió un asistente de IA a partir del README y el catálogo, sin revisión humana independiente. Las dos pasadas son del mismo autor: comprueban la coherencia con las reglas, no sustituyen a un segundo anotador.
- **Muestra pequeña:** 30 noticias, 17 riesgos, 8 urgencias y 20 pares de proveedor. Un solo error mueve precision y recall entre 5 y 13 puntos. Una sola ejecución no mide la variabilidad del modelo.
- **Sesgo optimista por diseño.** Solo hay casos inequívocos, así que no mide los casos dudosos, que son los que más fallan en la práctica, ni el ruido real del RSS. El reparto entre tipos no es el del mundo real.
- **Criterios propios en los extremos.** Los criterios «retraso ≤ 10 días = riesgo no urgente» y «cambio a ≥ 12 meses = estratégico» se derivan del README. Los moderadores podrían tener otra convención en casos parecidos, aunque se evitaron los intermedios.
- **No sustituye** la evaluación de test que hacen los moderadores ni certifica la calidad en RSS.
