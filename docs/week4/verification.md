# Evidencia de validación

Fecha de implementación: 2026-10-18. La evidencia cloud y la de código se mantienen separadas.

## Ejecutado localmente

- API: **28 tests pasaron**. Incluyen los 25 casos existentes y tres de observabilidad; no se usaron claves reales ni llamadas a Gemini. Starlette emitió una advertencia de deprecación de TestClient/httpx; no falló ninguna prueba.
- Herramientas: **16 tests pasaron**, incluyendo bloqueo de mutaciones Terraform, inventario incompleto, paquete sin secretos, revisión de notebooks, retries, versiones equivocadas, Jobs fallidos y costos sin datos.
- Alertas: **3 tests Node pasaron**, para crear/deduplicar incidentes, cerrar recuperación y separar simulacros.
- Sintaxis Python/YAML/Bash, `git diff --check` y formato Terraform: correctos.
- Terraform descargó AzureRM 4.81.0 firmado y generó el lock. La carga del plugin no funcionó en este runtime; la validación del esquema se deja al runner Ubuntu de CI, conservando la verificación de checksums.
- Docker no está disponible en esta terminal; el DAG se verifica en el job Docker de GitHub Actions.

## Lectura pública de Azure

El 2026-10-18 a las **19:31:03 UTC**, `/health` devolvió `status=ok`, primer intento, aproximadamente 3323 ms. En la revisión previa `/version` devolvió 404: esta versión con observabilidad todavía no estaba desplegada. No se puede deducir disponibilidad histórica ni funcionamiento de Gemini de un único probe.

## GitHub

El CI previo del usuario, sobre `1fdb1516ea5fa4f3c2bef761b8bb928e1fb75e17`, terminó correctamente: [run 39142041479](https://github.com/gusbakers/max1102-pipeline/actions/runs/39142041479).

Los nuevos commits tienen su evidencia en el [PR de semana 4](https://github.com/gusbakers/max1102-pipeline/pull/1) y [Actions](https://github.com/gusbakers/max1102-pipeline/actions/workflows/ci.yml). Consultar el SHA específico: el éxito del run anterior no valida estos cambios.

No se han ejecutado desde esta terminal imports/applies cloud, despliegues autenticados, consultas de facturación ni una presentación al equipo. No hay credenciales locales para esos proveedores.
