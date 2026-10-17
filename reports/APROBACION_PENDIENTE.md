# Autorizaciones y pendientes actuales

## Ya autorizado y ejecutado

- Push a GitHub `Mvr09/MAVERICKS-G12-mv`, rama `main`, conectada al autodeploy existente. Destino Railway `peaceful-harmony / production`; web, worker y PostgreSQL configurados por el usuario. No hay acceso directo al panel ni se pide token.
- Training inicial: 3 artículos, cuatro peticiones HTTP reales; cupo agotado. RSS inicial adicional: 10 artículos, diez peticiones, cupo agotado. No se reinician.
- URL real: https://mavericks-g12-mv-production.up.railway.app, target port 8000.

## Autorización nueva del usuario

El usuario autoriza **hasta 200 llamadas JEV adicionales en total**, y consultas RSS conforme a límites del proveedor. La propuesta antigua de 83 artículos/498 peticiones queda sustituida por este límite.

- Presupuesto compartido persistente `demo-final-200-20261017`: máximo 200 intentos HTTP registrados, incluidos reintentos, entre todos los workers, etapas y lotes. Caché válida no consume llamadas nuevas.
- Orden: validación (10 artículos), test (20), LiveDay (14). Después, RSS pendiente dentro del saldo y del límite diario de 100 artículos. No hay obligación de gastar el máximo.
- Ventana operativa: 45 minutos desde la primera llamada, sin renovación automática. No ajustar preguntas, umbrales, scores o reglas con validación, test ni LiveDay. Preguntas y política siguen congeladas en 1.0.0.
- Hasta tres intentos por etapa y 60 s por artículo; cuatro solicitudes HTTP simultáneas globales. Si 200 llamadas no bastan, detener y mostrar el estado pendiente/error, nunca escribir N por defecto.
- RSS gratuito continúa cada cinco minutos y bajo petición. Inferencia RSS periódica mantiene false; análisis manual adicional dentro del presupuesto compartido.
- Resultados completos y Excel de evaluación/fase final en `.runtime/final/` y `reports/private/`, excluidos de Git, Docker y assets. Informe público solo con metadatos y métricas agregadas.

## Pendientes no delegables al agente

Audibilidad física: usuario debe indicar dispositivo/navegador y resultado de activar/probar/silenciar/probar. La prueba móvil física fue omitida por decisión del usuario y no se dará por ejecutada. La limpieza de demo solo se ejecuta cuando el presentador confirme su alcance en la aplicación.
