# A14 · registro de sonido

**Estado actual: pasa.** El usuario confirmó una única alerta automática audible en ordenador/Firefox medianteQA5s, sin Probar alarma. La secuencia histórica y las pruebas complementarias se conservan debajo.

## Confirmación inicial del usuario

- Dispositivo: **ordenador**. Sistema operativo y modelo no indicados; no se inventan.
- Navegador: **Firefox**. Versión no indicada.
- Prueba confirmada inicialmente en esta conversación: **solo «Probar alarma»**. Sonido audible confirmado por el usuario.
- La declaración previa «funciona perfecto» respondía al guion Activar sonido → Probar alarma → Silenciar → Probar alarma. Se conserva como confirmación previa de sonido/silencio; no se transforma en prueba de disparo automático.
- Fecha exacta y commit en el momento de la prueba física no indicados. Se registra la declaración del usuario en18-10-2026, sin atribuir a una revisión concreta una prueba que no se fechó.

## Dos recorridos diferentes

1. **Botón Probar alarma:** después del gesto de activación llama a reproducción; el mute impide el sonido. Este es el recorrido físico confirmado en ordenador/Firefox.
2. **Nueva alerta elegible:** exige alerta nueva/no reconocida, sound_eligible=true, sonido activado/no silenciado, ventana de cooldown de30s y una emisión por revisión/pestaña. Se activa por el sondeo de alertas, no por pulsar Probar alarma. Este recorrido no se probó físicamente según la aclaración del usuario.

Los E2E históricos verifican gesto, historial silencioso, emisión única, cooldown, foco, mute y bloqueo del navegador con un AudioContext simulado. app/audio.ts y el disparo por alertas no cambiaron con la corrección de duración/texto. Se hereda esa prueba lógica, sin usarla como evidencia de audibilidad.

**Estado histórico antes de la nueva confirmación: no ejecutado completo.** Falta escuchar una nueva alerta elegible automática en ordenador/Firefox tras activar sonido. No se genera una alerta falsa presentada como real, ni se altera elegibilidad/revisión para forzar sonido. Si se usa un evento QA para probarlo, debe estar identificado y permanecer separado de las noticias reales/dataset.

## Control automático publicado18-10-2026

Commitb4d697b: botón de presentador «Programar alerta QA (5 s)». Tras activar sonido y esperar30s desde otra alerta automática, programa una señal claramente identificada. El mismo sondeo normal la entrega a audio.notify, no a play desde el botón. El escenario de elegibilidad determinista no es una clasificaciónJEV. No crea datos persistentes de cartera ni exportaciones.

Endpoint anónimo401; sesión real202. Playwright/Chrome real contra Railway verifica una emisión de oscilador, ninguna directa desde el botón,0JEV y cuatro viewports sin overflow. **No es audibilidad física.** El usuario recibe las instrucciones y responde «Todavía no la he probado». A14 continúa no ejecutado completo hasta confirmación de sonido automático en ordenador/Firefox.

## Confirmación física posterior · A14 cerrado

El usuario confirma en esta conversación: ordenador/Firefox, Activar sonido → Programar alerta QA (5 s) → una única alerta automática audible, sin pulsar Probar alarma. Registro18-10-2026, aplicación publicada b4d697b. No se conoce sistema operativo ni versión de Firefox. La fecha exacta de ejecución física no se ha indicado separadamente del registro.

**A14 pasa:** esta confirmación complementa las pruebas acreditadas de gesto, mute, cooldown30s, no reproducción del historial, una emisión por revisión y recuperación de foco/bloqueo. La comprobación publicada recorre el mismo sondeo/audio.notify. El escenarioQA no demuestra calidad de clasificaciónJEV ni sonido con pestaña cerrada/teléfono bloqueado.
