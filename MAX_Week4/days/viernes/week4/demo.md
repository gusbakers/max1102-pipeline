# Demostración de 8-10 minutos

1. Problema (1 min): reporte mensual manual, calidad y despliegues inconsistentes.
2. Arquitectura (1 min): Airflow coordina Databricks; S3/Snowflake y API Azure.
   Explicar si S3/Snowflake todavía usan snapshots manuales.
3. Código a despliegue (2 min): PR, CI verde, merge, deployment y /version.
4. Flujo de datos (2 min): una ejecución controlada, seis tareas, logs y reporte.
5. Operación (1 min): logs API, métrica, simulacro de alerta y recuperación.
6. IaC y costos (1-2 min): recursos importados, plan sin cambios, tabla de costos.
7. Límites (30 s): Airflow depende de Codespaces; F1 y monitor sin SLA.

| Evidencia | Dónde obtenerla | Resultado observado |
|---|---|---|
| PR con fallo esperado y luego pruebas verdes | GitHub Actions | Pendiente |
| SHA desplegado igual al commit | /version | Pendiente |
| API responde con Codespaces detenido | /health | Pendiente |
| Notebook correcto y ejecución de jobs | Databricks | Pendiente |
| DAG completo, incluyendo notify | Airflow | Pendiente |
| Suite real de calidad y reporte | Databricks quality_reports | Pendiente |
| Alerta recibida y siguiente ejecución verde | GitHub notificaciones | Pendiente |
| Inventario completo y plan 0 cambios | Terraform/HCP | Pendiente |
| Consumo, crédito, facturación separados | Portales de cada servicio | Pendiente |

No presentar como resultados reales los tiempos, conteos o ahorros no medidos.
No marcar el ticket de producción como completo mientras haya recursos fuera
de IaC, alertas sin probar o Airflow sin hosting persistente.
