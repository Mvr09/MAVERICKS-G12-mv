# Comparador y campañas privadas

## Consultar

En **Modelo → Comparar**, elige campaña, muestra y perfiles A/B. Training y validation están separados; ambos ya se inspeccionaron. Su agregado es descriptivo, no una validación independiente. Test y LiveDay no tienen etiquetas: no se calcula precisión ni se interpreta acuerdo como exactitud.

Las barras usan una escala común. La tabla contiene valores exactos y diferencias en puntos porcentuales. Cada celda de riesgo/urgencia filtra las noticias; abre evidencia y prioridad sin perder los selectores. La cobertura automática tiene su propio denominador y no equivale a precisión. Los errores entre automáticas contrastan riesgo, urgencia y conjunto de proveedores con las referencias conocidas. Las revisadas también entran en las métricas. Un fallo conserva decisiones nulas y se cuenta en la completitud.

La prioridad compara unidades noticia–proveedor; un valor ausente no es cero. Los tiempos separan espera en cola, suma de análisis y ventana real. La disponibilidad de resultados exportables y la descarga JSON no son un benchmark de exportación Excel ni renuevan A20. Las consultas y gráficos no ejecutan JEV.

**Ejecuciones** permite preparar una campaña privada y confirmar expresamente su inicio. **Histórico** conserva las evaluaciones anteriores recogidas por defecto. Los filtros se conservan en esta sesión del navegador. No se promueve un perfil automáticamente.

## Campaña nueva autorizada de 74 × 2

- 30 training y10 validation con referencia conocida;20test y14LiveDay sin referencia.
- Los cuatro originales se verifican contra `evidence/input_manifest.json`. No se busca ni abre answer key.
- La fuente se limita a los campos de inferencia. Las referencias están en `campaign_runs.reference`, fuera de prompts, recuperación y decisiones.
- El catálogo base de40 identidades, los textos, referencias, manifiesto y componentes semánticos quedan congelados por hashes. Baseline1.0.0 conserva sus preguntas/reglas y catálogo sin enriquecimiento; candidata3.4.2/revisión1.3.1 conserva su pipeline completo. Misma versión JEV1.13.0; no atribuir las diferencias solo al modelo base.
- Caché de inferencia histórica desactivada solo en la campaña. Se permite recuperar etapas válidas de la misma entrada/campaña tras una interrupción. Las respuestas originales y todos los intentos se conservan. No se repite una respuesta válida para mejorarla.
- Concurrencia4 y orden intercalado por fila original. Baseline tiene1–2 peticiones iniciales por noticia; la candidata añade etapas condicionales y particiones. Máximo técnico3108intentos incluidos reintentos,36por noticia candidata y6baseline; tres intentos por etapa y60s/artículo. Se contabiliza el número real, no148peticiones por148noticias.
- Las campañas no crean artículos, análisis, etiquetas, incidentes, avisos ni acciones operativos. Las decisiones humanas no afectan a su evaluación. Un401/error de contrato pausa antes de insistir; registrar diagnóstico permite continuar pendientes y conserva el caso fallido. Los leases agotados quedan como error explícito.

Comandos autorizados y explícitos:

```bash
.venv/bin/python -m scripts.prepare_campaign .runtime/campaign-private-input.json
# Solo ejecutar después de revisar el manifiesto. PostgreSQL aislado ya migrado:
DATABASE_URL='<PostgreSQL aislado>' CAMPAIGN_RUN_COMMIT='<commit>' \
  .venv/bin/python -m scripts.run_campaign .runtime/campaign-private-input.json
```

El ejecutor usa el mismo servicio que el worker. Reanudar el mismo nombre/entradas conserva válidas y contadores. No usa `pytest` raíz ni reimporta retenidos fuera de esta autorización. El RSS periódico de pago permanece desactivado.

## Importar una medición local en Railway sin repetirla

La campaña nueva se ejecutó en PostgreSQL local aislado por un HTTP401 inicial de presentador en Railway. El acceso se restableció tras la corrección del `.env` por el usuario; se publica mediante importación sin repetir inferencias. El JSON privado completo está en `.runtime/new-campaign-private-export.json`, fuera de Git y Docker. No publiques este archivo: contiene textos, referencias y respuestas privadas. Los agregados sin filas se registran en `reports/campaign-20261019-summary.json`.

Una vez que `ADMIN_PASSWORD` del `.env` local coincida con el servicio web:

```bash
.venv/bin/python -m scripts.publish_campaign .runtime/new-campaign-private-export.json
```

También puedes entrar como presentador → Modelo → Ejecuciones → **Importar resultados medidos** y seleccionar ese JSON. No inicia inferencias. La importación es idempotente, valida integridad/coherencia y rechaza sobrescribir resultados distintos. Guarda la infraestructura original y la fecha de importación; no simula llamadas realizadas desde Railway. Los intentos originales siguen en la base local y el detalle importado; no se fabrican filas HTTP nuevas en el consumo operativo.

Para preparar una evaluación realmente nueva, sube el JSON de entradas en **Preparar entradas congeladas** y confirma **Iniciar evaluación con llamadas nuevas**. No reutilices un nombre para otros textos o referencias. Cambiar preguntas tras mirar resultados exige otra versión y reconocer la reutilización de las muestras.

## Operación y rollback

Esquema0010 añade dos tablas de campañas. No modifica las tablas operativas0009 ni requiere variables nuevas en Railway. El predeploy existente aplica la migración. No degradar tablas con datos para revertir una interfaz: usar un commit hacia delante compatible con0010. Web y worker deben compartir revisión. Importaciones/campañas requieren presentador; sus referencias y exportaciones no son públicas.
