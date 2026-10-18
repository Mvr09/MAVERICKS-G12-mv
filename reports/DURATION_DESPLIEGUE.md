# Duración: publicación y comprobación en Railway

**Publicado en main y observado en web/worker:** `12c4dff59252acca6a122341ae36479c81041b0c`. Incluye `b29bb93` (extractor independiente) y `734b114` (auditoría/representación). Se revisaron cinco commits y17archivos pertinentes; sin secretos locales ni cambios ajenos. Paquete allowlist de71archivos, sin originales/secretos.

[Aplicación HTTPS](https://mavericks-g12-mv-production.up.railway.app). Verificación API final: 2026-10-18T15:20:43.160812+00:00. UI real: 2026-10-18T15:22:06.801Z.

## Respuestas observadas

- `/`, `/healthz`, `/readyz`, cuatro assets, catálogo RSS y ficha S024: HTTP200. Salud devuelve el SHA publicado; disponibilidad comprueba PostgreSQL/esquema0007. Catálogo:40proveedores. Ruta profunda `/proveedores/S024`:200.
- Worker online y compatible, con el mismo SHA. En la transición aparecieron heartbeats de la revisión anterior y se esperó a su vencimiento; no se dio por verificado antes de alcanzar compatibilidad.
- Configuración runtime: modelo jev-1.13.0, default1.0.0, experimental link-2.2.0, análisis periódicoRSS de pago=false. No se modificaron variables desde el panel.
- Consulta manual RSS: POST `/api/sources/sync` devolvió202 y seis trabajos persistentes. Todos terminan done en un intento; las seis marcas de consulta cambiaron. Peticiones JEV del contextoRSS:48→48.

| Fuente consultada desde Railway | HTTP | Resultado |
|---|---:|---|
| BioPharma Dive | 304 | Consulta condicional; sin cambios |
| EL PAIS Internacional | 200 | Respuesta recibida |
| EMA | 304 | Consulta condicional; sin cambios |
| GDACS | 304 | Consulta condicional; sin cambios |
| Supply Chain Dive | 304 | Consulta condicional; sin cambios |
| The Loadstar | 200 | Respuesta recibida |

Los cuatro304 son consultas reales condicionales, no cuerpos de noticias descargados de nuevo. No se presentan como noticias nuevas o análisis recientes. Las últimas consultas/éxitos y trabajos observados están en duration-railway-verification.json.

## Interfaz pública y exposición

Chrome sobre la URL pública, sin mocks, a360/390/768/1440px: ficha de proveedor y noticiaRSS existentes, contexto Noticias reales, aviso de exposición potencial, foco del selector de contexto y ausencia de overflow horizontal. Sin erroresJS ni solicitudes de mutación del navegador. Captura móvil360 revisada visualmente: las señales de identidad/compatibilidad y la aclaración sobre afectación individual se muestran con un análisisRSS previo. No se ejecutó un análisis para generar esta evidencia.

## Prueba JEV separada del despliegue

Seis sintéticos reales ejecutados desde desarrollo local:6/6duraciones correctas,12HTTP200/0reintentos de36máximo. Contador local241→253; reanudación con0llamadas nuevas.4exactas/2límites inferiores; citas y unidades preservadas. Todos continúan revisión/urgenciaN y se conserva la discrepancia de riesgo EN/ES. Indefinidos probados solo offline. No se atribuyen a Railway los5,598s medidos localmente, ni se presenta una mejora general del clasificador.

63unit pasan; buildTypeScript/Vite pasa. Evidencia del consumo en DURATION_RESULTADOS.md y duration-directed-results.json; raw/uso por petición en privado y PostgreSQL local.

## Límites y pendientes

- No queda un cambio necesario de panel para lo comprobado. No hay acceso directo al panel: logs internos de Build/Deploy, número de réplicas, variables completas y métricas de infraestructura solo pueden comprobarse allí si se necesitan. La evidencia aquí procede de respuestas HTTPS y presencia/trabajos del worker.
- Audio físico no se repitió en esta entrega. El usuario había confirmado su funcionamiento anteriormente; una nueva acreditación de audibilidad requiere dispositivo/navegador real y no se sustituye por Playwright.
- No se hizo ensayo nuevo de14artículos/300s ni evaluación test/LiveDay. Factorial aplazado; no se consultaron validation/test/LiveDay para desarrollar o ajustar esta entrega.
- Estos metadatos de verificación se guardan después del push en el workspace/commit documental local para conservar evidencia sin provocar otro autodeploy. El commit público comprobado sigue siendo12c4dff.
