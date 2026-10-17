# Evaluación del motor · separada de las etiquetas

Versión de preguntas 1.0.0, política 1.0.0 y modelo fijado jev-1.13.0. La congelación está registrada en `prompt-freeze.json`. No se han ajustado preguntas ni umbrales con validación, test o LiveDay.

La comprobación autenticada autorizada cubrió tres identidades de noticias de entrenamiento: N001, N002 y N005. Se realizaron cuatro peticiones (tres de etapa A y una de etapa B), todas HTTP 200 al primer intento; el modelo devuelto fue jev-1.13.0. Tiempo total local: 1,476 s. Uso agregado reportado por la API: 36.879 tokens de entrada y 3.284 de salida. No se conoce el cargo facturado ni se estima precisión a partir de estos tres ejemplos.

Validación retenida (10 noticias): **no ejecutada**, pendiente de autorización de consumo. Test (20) y LiveDay (14): **no ejecutados**, reservados para la fase final. No se publican etiquetas ni salidas protegidas del reto en este informe. No hay matrices de confusión, F1 o tiempos del lote final que se puedan afirmar todavía.

El endpoint protegido `POST /api/evaluations/{batch_id}` calcula matrices de riesgo y urgencia con precision/recall/F1, denominador n, exactitud del conjunto de proveedores y precision/recall por ID. Rechaza lotes incompletos y splits sin etiquetas. Tras ejecutar validación una vez, conservar el informe en `reports/private/`, excluido de Git y de la imagen. Si se cambiasen las preguntas a partir de ese resultado, documentar que la validación deja de ser independiente.

RSS: ingesta real comprobada; análisis de pago apagado por defecto. Las noticias RSS no alteran las exportaciones del ejercicio. Las pruebas con mocks son pruebas de software, no métricas de clasificación.
