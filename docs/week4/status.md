# Estado verificable de la semana 4

## Implementado en Git

- CI de API, DAG, herramientas operativas y definición Azure Terraform.
- Artefactos identificados por SHA; CD Azure con OIDC, gate de main y smoke de versión.
- Logs de solicitud sin cuerpos, cabeceras, parámetros privados ni claim IDs.
- Monitor público, deduplicación de incidentes, recuperación y simulacro aislado.
- Importación Terraform con rechazo de cambios a recursos y control de drift Azure opcional.
- Informe de costos que usa exportaciones reales y deja visibles los proveedores faltantes.
- Guion del viernes, pasos por día y recuperación.

## Activación externa pendiente

| Área | Evidencia que falta | Qué hace falta |
|---|---|---|
| Azure CD | Workflow de despliegue verde y `/version` con SHA | Ejecutar la activación en el Codespace con sesiones `az` y `gh` |
| Databricks | Exportaciones revisadas y run exitoso con ese código | Perfil MAX1102, IDs de Jobs, carpeta de notebooks y exportación real |
| Airflow permanente | Host encendido, despliegue y health verificados | Host existente elegido por el propietario; Codespaces no es un servidor permanente |
| Terraform | Recursos importados, estado remoto, plan vacío | Sesiones de proveedores, inventario real y backend autorizado |
| Monitoreo | Primer probe de main aprobado; comprobar simulacro y recepción de notificaciones | Ver verification.md; token/IDs para monitorear los Jobs |
| Costos | Importes del periodo y ahorro medido | Exportaciones Azure/AWS/Snowflake/Databricks/GitHub; no hay acceso a facturación aquí |
| Protección main | Checks obligatorios configurados | Administración de las reglas del repositorio |
| Demo del mes | Presentación al equipo y ejecución completa | Ejecución con datos sintéticos en el entorno del propietario |

No hay sesiones cloud en la terminal de implementación ni acceso al directorio `/workspaces/max1102-pipeline` del Codespace. La conexión a GitHub permite publicar el código; no concede permisos en los otros proveedores.

Las validaciones y runs específicos se registran en [verification.md](verification.md). Antes de cerrar el sprint, actualizar esta tabla con enlaces a pruebas reales; no marcar como terminado un job `skipped`.
