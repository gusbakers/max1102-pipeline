# Revisión de costos - completar con evidencia

Periodo UTC: [inicio] a [fin]. Fecha de consulta: [fecha].

| Servicio | Consumo observado | Cubierto por crédito | Facturado | Proyección/mes | Acción |
|---|---|---|---|---|---|
| Azure App Service / logs | Pendiente | Pendiente | Pendiente | Pendiente | Confirmar F1 y otros recursos |
| AWS S3 / solicitudes | Pendiente | Pendiente | Pendiente | Pendiente | Revisar tamaño y requests |
| Snowflake | Pendiente | Pendiente | Pendiente | Pendiente | Auto-suspend y consultas |
| Databricks | Pendiente | Pendiente | Pendiente | Pendiente | Revisar edición y cuota |
| GitHub Actions / Codespaces | Pendiente | Pendiente | Pendiente | Pendiente | Apagar Codespaces |
| Gemini | Pendiente | Pendiente | Pendiente | Pendiente | Revisar cuota y requests |
| HCP Terraform | Pendiente | Pendiente | Pendiente | Pendiente | Confirmar plan Free |

Proyección sencilla: costo observado / días observados * 30.
Solo usar si el patrón es representativo. Para cargas mensuales usar número de
ejecuciones * costo por ejecución + almacenamiento. No convertir créditos de
Snowflake en dólares sin comprobar la tarifa de la cuenta. Un presupuesto alerta;
no representa un tope automático de gasto. No inventar ceros si no hay evidencia.
