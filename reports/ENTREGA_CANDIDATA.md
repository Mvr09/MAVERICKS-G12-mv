# Entrega candidata: matching, QA y A20

## Decisión de versión

Estable1.0.0 conservado con extractor duration-1.1.0; link-2.2.0 experimental. geo-1.0.1 añade hechos geográficos a las preguntas originales sin cambiar las puertas de riesgo/urgencia. Perdió asociaciones correctas en training y no pasa a estable ni se ofrece como opción pública. Implementación, congelación y resultados quedan conservados. No hay excepciones por noticia ni cambios de umbrales/referencias.

Se comprobaron30training y6sintéticos con ambos perfiles. Una comparación retrospectiva después de congelar confirma que la pregunta inicial sigue rechazando exposición con geografía conocida. La provincia desconocida de S003 es otro problema, no una justificación para detener la investigación del proveedor con ubicación respaldada. Métricas/regresiones en GEOGRAFIA_AISLADA.md; referencias por noticia privadas.

## Prueba física A14 para el usuario

1. En ordenador/Firefox, entrar como presentador y pulsar Activar sonido.
2. Esperar30segundos desde la última alerta automática si la hubo.
3. Pulsar **Programar alerta QA (5 s)**. Para esta comprobación no pulsar Probar alarma.
4. Mantener la pestaña abierta y esperar al sondeo posterior a los5segundos (normalmente5–8s).
5. Escuchar y comunicar si sonó una sola vez. La indicación visual de entrega no demuestra audibilidad.

El botón programa; no llama directamente a play. El mismo sondeo normal entrega la señal a audio.notify: mismos mute, cooldown y emisión única. La elegibilidad procede del mismo evaluador determinista con un escenario QA declarado, no de una clasificación JEV. Endpoint con acceso de presentador/CSRF. No crea artículos, incidentes, proveedores, alertas persistentes de cartera ni exportaciones; la señal temporal pertenece a la pestaña y desaparece al recargar/cerrar. No es un resultado de negocio en filesystem.

Probar alarma ya tiene confirmación física en ordenador/Firefox. La prueba automática nueva permanece pendiente de la respuesta del usuario. Osciladores/estados de Playwright no se contabilizan como audibilidad.

## Una sola ejecución final A20

Después de publicar el commit congelado, scripts/final_a20_once.py verifica revisión, worker, modelo y perfil. Reanaliza solo LiveDay14 con generaciones nuevas, preserva los resultados previos y mide con reloj monotónico desde el POST hasta recibir el Excel, incluidos cola/reintentos/descarga. No carga answer key ni calcula precisión de test/LiveDay; no ajusta reglas con sus salidas.

Máximo técnico:14artículos×2etapas×3intentos=84HTTP. Los contadores persistentes no se reinician. El registro privado se escribe antes del POST; un fallo no inicia otra medición. Registra llamadas nuevas frente a caché y verifica hashes de los resultados históricos. Exportación privada y agregado sin respuestas en a20-current-results.json. Fuente completa pertinente fijada en final-candidate-freeze.json; medición histórica separada. Factorial aplazado y RSS periódico de pago=false.

## Verificación previa

70pruebas unitarias/integración con catálogo sintético pasan sin abrir Excel.4E2E del perfil pasan; el nuevo QA pasa en10,4s. El primer intento de ese E2E no programó una señal porque el selector móvil de activación era ambiguo; selector corregido. TestClient dentro del sandbox se bloqueó: detenido y repetido con permisos locales,70pasan con aviso externo AnyIO. TS/Vite y paquete74archivos sin secretos/originales pasan. No se ejecutó la suite antigua que importa los cuatro Excel durante desarrollo.
