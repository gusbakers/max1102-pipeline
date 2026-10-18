# Operación y recuperación

## Un CI rojo

Abrir el job y el primer paso fallido. Reproducir con los comandos del lunes. Corregir mediante PR; no activar CD ni quitar checks para pasar. El job `check-dag` necesita Docker y el mismo Python/provider de Airflow.

## Azure desplegó pero falló el smoke

1. Identificar el SHA y run fallidos. Probar `/health` y `/version`; revisar los logs sanitizados, configuración de inicio y construcción de dependencias en Azure. Los códigos 503 por falta de claves no se solucionan publicando claves en Git.
2. Si el artifact nuevo dejó el servicio mal, revertir el commit causante mediante un PR (`git revert <SHA>` sobre una rama limpia), pasar CI e integrar. CD publicará un artifact nuevo, probado, cuyo `/version` coincida con el nuevo commit de reversión.
3. No volver a construir un ZIP antiguo desde una carpeta con cambios sin commit. Si se necesita recuperar antes de completar el PR, usar un artifact anterior conservado de un run verde desde la terminal Azure autenticada, documentar el SHA anterior y reconciliar Git después.
4. Verificar `/health`, versión y una petición sintética autorizada. El rollback de código no cambia automáticamente secretos, estado de Terraform ni datos; no borrar ninguno como parte de la recuperación.

No se implementa rollback ciego que pueda ocultar un fallo. Un smoke fallido conserva el run rojo y exige recuperación verificada. El plan F1 no permite asumir slots/blue-green ni disponibilidad sin interrupciones.

## Alerta de monitor

El Issue incluye fecha y enlace al run. El monitor distingue producción y simulacro. Revisar disponibilidad, cambios recientes y autenticación de Databricks si está activa. Un error de credenciales de Jobs es monitoreo incompleto y debe resolverse; no equivale a Jobs sanos. Los detalles internos del proveedor no se imprimen.

No cerrar el incidente para simular recuperación: ejecutar otro probe real. Cuando pase, el workflow registra y cierra automáticamente su incidente. Revisar Watch/Notifications de GitHub para confirmar quién recibe avisos; esta entrega no configura correo ni Slack.

## Notebook importado parcialmente

Mantener el DAG y schedules pausados. No lanzar Jobs mientras se importa el conjunto. Restaurar las exportaciones de respaldo de los notebooks afectados y comparar rutas/configuraciones de los cuatro Jobs. Revisar un run sintético antes de reabrir la ventana. Imports de workspace separados no son una transacción.

El manifiesto controla la revisión del código; los Job IDs, rutas, permisos y la ejecución real siguen requiriendo verificación. La exportación actual de Git está incompleta y el deploy se bloquea hasta reemplazarla con la fuente operativa revisada.

## Terraform detecta drift

No ejecutar apply desde Actions. En una terminal autorizada, abrir el estado remoto correcto y producir un plan privado; clasificar cambio esperado, modificación manual o error de configuración. Actualizar HCL mediante revisión. Durante la adopción, el gate admite solo imports y no-ops. Nunca usar `terraform destroy` para resolver un problema de importación.

## Airflow

Consultar `ops/airflow/README.md`. Conservar Postgres y logs. Si la restauración automática falla, usar la release indicada en `/opt/max1102/previous-release`, con el mismo proyecto Compose y volumen. Comprobar health, errores de importación y estado del DAG antes de despausar. No hacer rollback de base de datos cambiando imágenes a ciegas.

## Cierre de una incidencia

Registrar impacto, hora inicial/final, SHA, causa confirmada, acción correctiva y evidencia de recuperación. Distinguir hipótesis de hechos. Usar datos sintéticos y excluir tokens, cuerpos de claims, `.env`, state y planes con valores sensibles.
