# Entrega opcional a un host de laboratorio existente

La pila Compose del repositorio es para laboratorio. Usa Postgres/Redis locales y no debe exponerse como una instalación productiva. Este procedimiento no crea un servidor; si solo existe Codespaces, sigue pendiente un alojamiento permanente.

## Preparación de una sola vez

El propietario debe disponer de un host dedicado, Docker/Compose, Python 3, curl, tar y flock. La cuenta SSH de despliegue puede operar Docker; tratar ese permiso como privilegiado. Mantener el API de Airflow ligado a loopback; acceder por túnel SSH o un acceso privado aprobado.

Establecer una **release base funcionando** bajo `/opt/max1102/releases/<SHA>/`, imagen `max1102-airflow:<SHA>`, proyecto Compose `max1102` y:

- `/opt/max1102/current`: enlace a esa release.
- `/opt/max1102/shared/airflow/{dags,logs,config,plugins}`: `dags` enlaza al código de la release; los demás directorios persisten, con permisos para AIRFLOW_UID.
- `/opt/max1102/.env`: configuración real, FERNET_KEY y JWT secret fuertes, usuario/contraseña de laboratorio diferentes de los defaults, conexión Databricks; modo 600. No regenerar FERNET_KEY sobre datos existentes.
- Volumen persistente de Postgres asociado al proyecto `max1102`, con respaldo probado.

Inicializar esa base con el procedimiento de Airflow del proyecto, revisar que los cuatro componentes estén sanos y que no haya errores al importar DAGs. Crear `DEPLOYMENT_READY` solo después de esa verificación. Este bootstrap necesita validar la ruta/propietario y almacenamiento del host real; no hay uno configurado en esta entrega.

En GitHub configurar `AIRFLOW_HOST`, `AIRFLOW_USER`, `AIRFLOW_SSH_KEY`, `AIRFLOW_KNOWN_HOSTS` y finalmente `ENABLE_AIRFLOW_CD=true`. Verificar la huella SSH por un canal confiable antes de guardarla; el script exige StrictHostKeyChecking y no acepta claves de host automáticamente.

## Cada release

1. Abrir una ventana de mantenimiento: pausar el DAG, impedir disparos externos/manuales y dejar terminar los Jobs. No interrumpir ejecuciones activas.
2. En el host guardar el SHA exacto probado en `/opt/max1102/APPROVED_COMMIT`. Es una autorización de una sola release. El script verifica además que el DAG esté pausado y que no haya runs queued/running.
3. Solicitar `ci.yml` en main con `deploy=true` o integrar el commit aprobado. El job descarga el artifact del mismo workflow y ejecuta el script por SSH.
4. El script bloquea despliegues concurrentes, construye la imagen, conserva datos/logs y exige que el Dockerfile no cambie. Las migraciones de Airflow/proveedores requieren un procedimiento separado.
5. Comprueba el JSON de `/api/v2/monitor/health` y los errores de importación; no basta HTTP 200. Ante un fallo, intenta restaurar la release anterior. Si falla esa restauración, requiere intervención del operador.
6. Revisar health y una ejecución sintética antes de despausar. Una release fallida permanece para diagnóstico y bloquea reintentar el mismo SHA hasta inspeccionarla.

Es una entrega automatizada **dentro de una ventana operativa aprobada**, no CD desatendido ni evidencia de producción 24/7. No usar `docker compose down -v`, no borrar la base de datos y no cambiar la versión de Airflow desde este camino de rollback.

Referencia: [health de Airflow 3.2](https://airflow.apache.org/docs/apache-airflow/3.2.0/administration-and-deployment/logging-monitoring/check-health.html).
