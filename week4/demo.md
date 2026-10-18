# Viernes — presentación del mes (12–15 minutos)

## 1. Problema y resultado esperado (1 min)

“Partimos de un reporte mensual ejecutado con pasos manuales. Organizamos ingesta, validación, transformación y carga, expusimos una API y añadimos controles de entrega y operación.” Mostrar el estado real de `docs/week4/status.md`: explicar cualquier activación pendiente.

## 2. Arquitectura y semanas 1–3 (3 min)

Mostrar datos sintéticos de claims/providers y recorrido por S3/Snowflake/Databricks según el flujo que realmente esté configurado. No afirmar una integración solo por su presencia en un diagrama.

Airflow coordina prepare → extract → validate → transform → load → notify. Explicar month/raw_dir/batch_id, rechazos de calidad, reporte por especialidad, filtro PAID y reemplazo del mes. Mostrar evidencia de una segunda ejecución idempotente y un registro inválido rechazado, cuando se hayan ejecutado realmente en el workspace.

La API usa X-API-Key, valida entradas, minimiza el prompt y sanea errores del proveedor. Mostrar tests sin gastar cuota de Gemini; una demo real usa exclusivamente datos sintéticos.

## 3. Semana 4: cambio hasta Azure (3 min)

Abrir un PR con una modificación pequeña y verificable. Enseñar los cuatro checks, artifacts por SHA y gate de main. Tras integrar y con CD activado, abrir el run de despliegue y consultar `/version`: debe coincidir con el commit probado. Si CD está skipped, mostrar su configuración pendiente y no presentarlo como un despliegue exitoso.

Explicar que el código probado se empaqueta una vez. Mostrar el inventario del ZIP, sin `.env` ni tests, y un log JSON con ruta, status, duración y request ID.

## 4. Infraestructura y operación (3 min)

Mostrar HCL y estado remoto con recursos importados, únicamente si la adopción se completó. Compartir el resumen saneado de `plan` sin cambios; no abrir state o plan JSON en una reunión.

Ejecutar el simulacro de monitor (`fail`) y luego la recuperación (`recover`); abrir su Issue separado. Explicar retries, frecuencia horaria y límites de un schedule de GitHub.

Presentar un costo observado por proveedor, periodo y unidad. Si faltan exportaciones, mostrar los pendientes; no reemplazarlos por ceros. Explicar una optimización con medición antes/después cuando exista.

## 5. Recuperación y entrega (2 min)

Recorrer `docs/week4/runbook.md`: rollback mediante revert probado, restauración de notebooks, drift sin apply automático y conservación de datos. Explicar quién opera cada componente y qué queda pendiente de acceso/hosting.

## Lista de evidencias para cerrar

- [ ] PR y CI verde del commit presentado.
- [ ] Prueba de que un fallo de CI bloquea la integración/despliegue; reglas main activas.
- [ ] CD real de API y `/version` con SHA coincidente.
- [ ] Run real del DAG, controles de calidad e idempotencia con datos sintéticos.
- [ ] Fuentes Databricks revisadas y entrega al workspace comprobada.
- [ ] Host Airflow y persistencia verificados, o limitación del Codespace declarada.
- [ ] Terraform importado, estado remoto y plan vacío de cada proveedor incluido.
- [ ] Probe real, incidente de simulacro y cierre de recuperación.
- [ ] Costos exportados, decisión y ahorro medido cuando corresponda.
- [ ] Runbook y responsables revisados con el equipo.

No hay una reunión ni mensajes enviados al equipo por esta entrega. Este archivo es el guion listo para usar, no evidencia de que la presentación ocurrió.
