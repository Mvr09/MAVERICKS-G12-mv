# Operación diaria: revisión y seguimiento

## Bandeja de noticias

En Noticias reales, los indicios de nombre, lugar o corredor ayudan a priorizar lectura. No confirman asociación, riesgo, urgencia ni entregas afectadas. Un país por sí solo no prioriza la cartera. Una noticia sin indicio sigue disponible y puede analizarse; no se descarta automáticamente.

Usa los filtros habituales y «Con indicios preliminares». El filtro «Trabajo de revisión» separa pendiente, en verificación, resuelta y asociaciones rechazadas con evidencia. Los descartes permanecen guardados. El indicador de actividad conserva cambios de análisis y revisiones desde la última consulta del navegador; no reproduce alertas sonoras históricas.

Como presentador, abre «Seleccionar noticias para análisis manual». Selecciona hasta diez, revisa títulos, perfil y máximo técnico, y confirma. Se muestran cola, avance, peticiones y errores por trabajo. Un error no significa sin riesgo: abre su noticia y usa el diagnóstico/reintento explícito existente. «Limpiar selección» prepara otro lote sin borrar noticias ni consumo. El RSS periódico de pago sigue desactivado.

Para trabajo asistido se recomienda la candidata3.4.2/revisión1.3.1. Sigue siendo una elección explícita;1.0.0 permanece predeterminada. Las versiones quedan fijadas por trabajo. No se promueve el modelo con los resultados de decisiones humanas.

## Resolver una revisión

1. Abre una noticia analizada y «Revisión humana». Los análisis automáticos sin dudas no crean trabajo obligatorio: permiten una revisión opcional.
2. Elige el proveedor. Contrasta la predicción, la evidencia y el dato que falta. Si la ciudad es ambigua, solicita provincia/dirección; si falta una ruta, confirma el servicio o las entregas. S003 conserva provincia desconocida: no se elige una por su nombre. S024 tiene Hangzhou→Zhejiang respaldado; eso no prueba entregas individuales afectadas.
3. Para información pendiente, conserva «Falta información» y guarda una solicitud concreta. Para cerrar, confirma o rechaza con evidencia, procedencia y observación. En asociación confirmada, decide riesgo y urgencia por separado; una noticia positiva puede conservar proveedor sin riesgo. Para riesgo positivo indica una severidad humana explícita; no se copia la estimación JEV automáticamente.
4. Distingue exposición potencial de afectación individual confirmada por evidencia. Si quedan dudas generales del análisis, no basta cerrar un proveedor: contrástalas y confírmalo explícitamente. Si no tienes información, mantén verificación.
5. Para añadir contexto sin cambiar la decisión, utiliza «Añadir observación sin cambiar decisión».

Cada registro es nuevo e incluye actor compartido, momento, fuente, versión, generación, análisis asociado y política humana. Las notas y evidencias humanas solo se leen como presentador. La lectura pública contiene decisiones normalizadas, sin notas privadas. No se atribuye identidad individual a una cuenta de presentador compartida.

**JEV, sus etiquetas de evaluación y la exportación del reto no se modifican.** Las correcciones humanas cambian la gestión operativa y sus incidentes; no mejoran retrospectivamente las métricas ni se incorporan automáticamente a training. Se conservan las probabilidades originales, sin convertirlas en1. Si JEV no evaluó ese candidato se indica «no estimada», no cero. Una solicitud nueva con información ausente sigue pendiente. La política humana vigente es human-review-1.0.1; se conservan las decisiones anteriores con su versión. Las alertas nuevas de origen humano son visuales; no se inventa confianza para habilitar sonido.

Una revisión de una noticia tampoco silencia otra evidencia urgente del mismo incidente: la urgencia operativa conserva su fuente y explicación.

Un reanálisis o cambio de fuente conserva las decisiones anteriores como históricas. La versión sustituida no admite nuevas decisiones; ofrece un enlace a la fuente vigente. Una actualización válida retira efectos antiguos sin simular recuperación; si falla, conserva el último estado conocido. No se aplican silenciosamente a la nueva ejecución. Los formularios detectan conflictos; recarga la revisión y contrasta el nuevo contexto, conservando tu texto. Rechazar una asociación retira solo la contribución de esa noticia; otra evidencia del incidente continúa vigente. No equivale a recuperación.

## Acción por incidente

En la ficha del proveedor, cada incidente conserva materiales, productos mapeados, factores, alternativa y evidencia. «Acción y seguimiento» registra acción concreta, estado, fecha y resultado: pendiente, en verificación, seguimiento o completada. La siguiente acción aparece en la lectura de compras de ese incidente.

Completar una acción no resuelve el incidente. Usa «Resolver incidente» solo con evidencia de normalización. Un incidente cerrado no se reabre por una revisión humana ni por noticias antiguas.

Las consultas al proveedor o alternativo quedan ligadas al incidente; se guardan, reabren y editan. Se conserva un snapshot de contexto en las nuevas consultas y se indica si el incidente cambió después. Confirma adecuación, disponibilidad, capacidad y plazo del alternativo: conocer su oferta no acredita stock. No se envían comunicaciones.

## Persistencia y despliegue

Migración aditiva **0009**: tablas `human_decisions` e `incident_work`. Web y worker requieren el esquema vigente; el predeploy existente ejecuta `alembic upgrade head`. No requiere variables nuevas. `.env` local no configura Railway.

La limpieza de demo bloquea selecciones que borrarían decisiones humanas o acciones; permite reanálisis conservando histórico. No hay borrado automático de esos registros. La reversión0009 se bloquea si contiene datos. Un rollback de aplicación debe hacerse mediante un commit hacia delante que conserve tablas y compatibilidad de readiness/worker con0009; no degradar ni eliminar registros para volver a0008.

Para comprobar sin conjuntos retenidos:

```bash
DATABASE_URL='<PostgreSQL aislado radar_test>' .venv/bin/python -m pytest tests/unit -q
npm --prefix frontend run build
E2E_URL='http://127.0.0.1:4173' npm --prefix frontend run test:e2e -- operational-review.spec.ts incident-work.spec.ts
```

Los tests UI utilizan mocks identificados. El diagnóstico offline de indicios usa solo resultados de training ya almacenados y sintéticos; no ejecuta JEV. A06 sigue abierto; A14 conserva la prueba física de ordenador/Firefox y A20 su medición histórica. No ejecutar LiveDay durante estas iteraciones.
