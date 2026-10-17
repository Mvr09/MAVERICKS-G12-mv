# Supplier Risk Radar · estado y continuación

## Estado verificado · 18-10-2026 (Madrid)

- Aplicación publicada: **2650ea7041abdd0b6928eaf22b616ff96a70e561**, `origin/main`, Mvr09/MAVERICKS-G12-mv. Railway peaceful-harmony / production: web, worker y PostgreSQL; ambos despliegues GitHub success. Sin acceso directo al panel.
- URL real: https://mavericks-g12-mv-production.up.railway.app. Smoke 17-10 22:19:24 UTC: /, /healthz, /readyz, catálogo, fuentes, configuración y cuatro assets **200**; esquema0006. Worker online/compatible en la misma revisión.
- Persistencia 22:20:35 UTC:40 proveedores,20 materiales; validation10/test20 procesados y Excel200 idénticos celda a celda tras redeploy. Training/LiveDay ya no están cargados: el agente no los borró ni reimportó. RSS37 procesados (23review/14done), seis fuentes saludables200/304. No se ejecutó borrado ni reanálisis remoto durante esta ampliación.
- Interfaz/documentación en español. Materiales, dashboard/fichas, fuentes/stream, filtros, ingestión/exportación, permisos, audio y borradores operativos. Servidor0.0.0.0:8000, web/worker misma imagen, predeploy `python -m app.predeploy`.

## Última ampliación: selección de demo y reanálisis

- **Preparar demo**: checkboxes sin selección inicial por lote Excel/fuente RSS y catálogo; elegir borrar o reanalizar; revisar alcance y confirmar LIMPIAR DEMO o REANALIZAR. Selección/modo vinculados a preview firmada, caducidad15min y validación de cambios. Trabajos activos bloquean la operación.
- Borrar lote permite recargar Excel; RSS conserva fuente y reinicia cabeceras condicionales para consultar de nuevo. Catálogo solo se borra con todas sus noticias dependientes. Incidentes compartidos conservan evidencias restantes y recalculan estado; avisos/borradores dependientes se incluyen en alcance. Un aviso regenerado por limpieza no emite sonido.
- Reanalizar conserva noticia e historial de resultados; generación nueva con consultas, caché e intentos separados. Vistas/ranking/exportación usan solo generación vigente; exportación pendiente hasta terminar. Solo se reanalizan versiones vigentes. Historial accesible al presentador desde la noticia.
- Consumo y registro diario RSS sobreviven a borrado/recarga. Corrección2650ea7 verifica el díaUTC antes de reutilizar reservas y asigna nuevos reanálisis/contrastes al permiso ilimitado vigente. Intentos/resultados antiguos no se reinician.

## Contraste RSS con tres evaluaciones

- Diagnóstico real previo:16 noticias con event_type_confidence_low y17 con event_state_confidence_low (solapados). Documentación primaria consultada: https://docs.typesafe.ai/confidence. No se cambiaron preguntas, política, modelo ni umbrales para reducir revisión.
- Botón **Contrastar con3JEV** en RSS: tres evaluaciones nuevas de jev-1.13.0, dos etapas cuando hay candidatos, hasta18peticiones incluidos reintentos. Votos y progreso persistentes; fallos no son N. Es auxiliar: no modifica análisis vigente, prioridad, alarmas ni exportaciones, ni elimina revisión por mayoría.
- Primer ensayo real e3b120f:1RSS,3peticiones nuevas,3/3votos revisión y original idéntico. La reserva antigua no tenía budget_id; sus llamadas están registradas por run_key pero no incrementaron el nuevo presupuesto (45→45). Se conservó esa evidencia y se corrigió la asignación.
- Ensayo final2650ea7:1RSS,3peticiones nuevas,3/3votos revisión; contador vigente **45→48**, original idéntico. Total de esta ampliación:6peticiones reales, ninguna altera decisiones del ejercicio. Son consultas del mismo modelo, no expertos independientes.
- Evidencia: reports/demo-comparison-railway.json, demo-comparison-railway-accounting.json, demo-ui-real.json, public-deployment-demo-selection.json y demo-selection-persistence.json. Observaciones posteriores al último push se registran localmente sin provocar otro autodeploy por metadatos.

## Pruebas

- **73 backend/integración pasan** sobre PostgreSQL dedicado radar_test; mocks identificados. Incluyen9pruebas nuevas de selección, recarga, incidentes compartidos, archivo de generaciones, consultas frescas, permisos, votos, errores y cambio de díaUTC.21regresiones dirigidas también pasan. Una deprecación Anyio externa.
- **16 E2E pasan**, con mocks identificados:360/390/768/1440, teclado, materiales, RSS, borradores/TXT, carga/exportación y audio lógico; nuevas selección/confirmación/reanálisis a360/1440 y contraste. Primer intento falló por aviso de fixtures desactivado en servidor E2E: corregido su entorno, suite completa pasa.
- UI real Railway sin mocks a360/1440:9opciones, selección inicial vacía, previews borrar/reanalizar200, cancelación conserva lotes, sin overflow ni erroresJS; tres votos reales visibles y revisión original conservada. Capturas demo-real-360/1440 y demo-selection-360/1440 (estas últimas mocks). Espaciado móvil corregido tras revisión visual.
- Build TS/Vite pasa; migración0006 pasa en base local aislada (22tablas), paquete permitido56archivos sin originales/secretos. Railway construyó/desplegó imagen. Docker local no disponible.
- Comandos: `DATABASE_URL=<radar_test> .venv/bin/python -m pytest -q`; `npm --prefix frontend run build`; `python -m tests.setup_e2e`; `E2E_URL=http://127.0.0.1:8001 E2E_FULL=1 npm --prefix frontend run test:e2e`; `python -m scripts.check_migrations`; `python -m scripts.package_deploy`; `python -m scripts.check_public_deployment --expected-commit <SHA>`.

## Autorización y seguridad

- Push/autodeploy autorizado a main. JEV manual **sin cupo ni vencimiento**, autorización explícita vigente del usuario. Presupuesto manual-unlimited-20261017 observado48; no se infiere saldo monetario. Pago periódico RSS siguefalse; consultas gratuitas cada300s. Límite técnico RSS100artículos/díaUTC, concurrencia4, hasta3intentos por etapa y diagnóstico ante autenticación/contrato.
- Historial conservado:3training iniciales N001/N002/N005,4peticiones reales locales; primerRSS10artículos/10peticiones; presupuesto final200 usó100 y venció22:01:52UTC. Nunca reiniciar esos contadores ni ampliar sus ventanas.
- .env no mostrado/modificado/empaquetado; variables requeridas configuradas. Credenciales solo runtime autorizado, sin valores/fragmentos/hashes en informes. Usuario compartió contraseñaBD en chat: no copiada a archivos; recomendada rotación en panel. No crear recursos Railway desde esta sesión.
- Preservados cambios ajenos: evidence/validation_report.json y archivo sin seguimiento ajeno; capturas antiguas regeneradas no añadidas. No buscar/abrir answer key ni modificar originales. Etiquetas separadas de inferencia y acceso público.

## Ensayo final histórico y pendientes

- Ejecución4a3645a, modelojev-1.13.0, preguntas/política1.0.0 congeladas. Validación10:670,043s incluidos diagnóstico/reintentos;18peticiones. Test20:5,763s/30peticiones. LiveDay14+Excel:5,753s/23peticiones, <=300s medidos realmente. Excel privados .runtime/final; detalles reports/private; no publicados ni Git.
- Validación n10: riesgo P1/R0,60/F10,75, dos falsos negativos de5positivos; urgencia P/R/F11 (2positivos); proveedores exactos8/10, revisión8/10. No se ajusta con esos resultados. Incidencia Score diagnosticada con SDK oficial; adaptador conserva valor del proveedor y no impone igualdad decimal inventada. Errores/intentos históricos conservados.
- Auditoría histórica:18pasa, A06falla (1/2casos múltiples exactos), A14incompleto solo por dispositivo/navegador. Usuario confirmó «funciona perfecto» para activar/probar/silenciar/probar; falta registrar esos metadatos. Móvil físico omitido por el usuario.16tests de referencia pasan, sin API. No declarar aceptación completa ni que el contraste haya arreglado A06.
- Siguiente: usuario puede probar selección/borrado/reanálisis tras recargar la web. No borrar, reimportar ni recalcular automáticamente más datos. Una mejora de matching requiere entrenamiento y evaluación independiente, sin ajustar sobre resultados retenidos.

## UX: decisiones legibles e historial automático · 18-10-2026
- Petición del usuario: sustituir Y/N visibles y evitar refresco manual del historial al reanalizar. Ficha, votos e historial ahora muestran Riesgo detectado/Sin riesgo detectado y Urgente/No urgente; valores ausentes se indican sin determinar.
- El historial abierto carga al cambiar noticia/generación/estado, ignora respuestas obsoletas y los eventos de sus detalles hijos; mantiene entradas expandidas e indica carga/error. Usa la consulta existente de la noticia cada3s para detectar la finalización.
- Build TS/Vite pasa;17E2E pasan con mocks identificados. Nueva regresión ejecuta el flujo completo pendiente→terminado sin page.reload, verifica nueva generación en el historial abierto, conserva la entrada anterior abierta y comprueba palabras en ficha/historial. Contraste también verifica etiquetas legibles. No se ejecutaron llamadas JEV reales para este cambio de interfaz.
- Se prepara push/autodeploy ya autorizado; incluye el commit documental local070aff9 de la entrega anterior. Cambios ajenos y capturas antiguas quedan fuera.
