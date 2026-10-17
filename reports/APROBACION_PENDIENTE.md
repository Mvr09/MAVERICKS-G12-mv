# Propuesta concreta de publicación y ensayo

No ejecutada. Esta propuesta no concede permiso por sí misma.

- Repositorio de trabajo: `Mvr09/MAVERICKS-G12-mv`, rama local `main`. Publicación mediante el paquete permitido `.runtime/deploy`; no requiere git push ni subir los Excel originales ya presentes en el historial local.
- Destino propuesto: proyecto Railway nuevo `supplier-risk-radar`, entorno `demo`, en el workspace que el usuario autorice. Crear web, worker y PostgreSQL con volumen. Dominio HTTPS solo en web. Configuración por `railway.web.json`/`railway.worker.json`.
- Acciones externas: crear/vincular los tres servicios; configurar variables en backend; subir código limpio; build, migraciones y despliegue; carga privada de catálogo/noticias por presentador o migración de resultados existentes; generar dominio y smoke test; un redeploy controlado para verificar persistencia. No conectar correo ni mensajería.
- Accesos pendientes: sesión de Railway o `RAILWAY_TOKEN`, workspace/proyecto de destino; `DATABASE_URL` de los servicios y `APP_BASE_URL` final. Las tres credenciales de aplicación ya existen y no hay que volver a pegarlas ni regenerarlas.
- Recursos de pago propuestos: web y worker durante la demo y PostgreSQL persistente. No se crean antes de autorizar; el coste exacto depende del plan/cuenta Railway y no se ha consultado un saldo.

## Ventana de inferencia propuesta, adicional al cupo inicial ya agotado

Una sola ventana de hasta 45 minutos tras autorización, sin renovaciones automáticas. Hasta **83 artículos nuevos**: 27 restantes de entrenamiento, 10 validación, 20 test, 14 LiveDay y 12 RSS (hasta dos por fuente). Si una fuente no publica dos noticias elegibles, se analiza solo lo disponible. Entrenamiento y validación pueden completarse antes de publicar; test y LiveDay únicamente en fase final autorizada. Las preguntas ya están congeladas; no se reajustan con validación/test/LiveDay.

Dos etapas agrupadas por artículo cuando haya candidatos, máximo tres intentos por etapa (dos reintentos), hasta **498 peticiones** en el peor caso, cuatro simultáneas, 15 s por intento y 60 s por artículo. 400/401/422 o error de contrato interrumpen para diagnóstico. La caché válida no cuenta como solicitud nueva. Se registran intentos/duración/modelo/uso. RSS se desactiva otra vez al terminar la ventana o agotar su grant; el cupo técnico de 100/día sigue vigente y no amplía esta autorización.

Preservar resultados ya obtenidos al preparar el entorno final; no repetir N001/N002/N005 para aparentar una prueba nueva. Medir una ejecución final completa de LiveDay desde su encolado en Railway hasta disponer del XLSX, incluyendo reintentos. No se presupone que cumpla 300 s. Ensayar audio con un dispositivo físico y registrar navegador/volumen.

## Estado revisable antes de la aprobación

Código y lockfiles; migraciones congeladas; Dockerfile no privilegiado; Compose; web/worker; controles de permisos/consumo; importación/exportación; seis RSS conectados; documentación española; pruebas y auditoría. Build de frontend probado. La construcción de imagen sigue pendiente de un Docker disponible o del build autorizado de Railway. No existe URL pública todavía.
