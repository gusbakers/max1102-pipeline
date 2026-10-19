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

La implementación `599448f9fd1c2d0b43b78f0e15fbec61fc9c1a36` pasó el [CI completo 39159473319](https://github.com/gusbakers/max1102-pipeline/actions/runs/39159473319), incluyendo `check-dag` en Docker y `terraform-validate` en Ubuntu. Esto resuelve las limitaciones de validación local descritas arriba.

El [PR #1](https://github.com/gusbakers/max1102-pipeline/pull/1) se integró en main como `9f806c1448ca9e2e08d1b3560ff22bf8fc931498`. El [monitor de producción 39159578309](https://github.com/gusbakers/max1102-pipeline/actions/runs/39159578309) completó correctamente su primera ejecución sobre ese commit.

`monitor-drill.yml` verifica el ciclo real de un Issue de simulacro en GitHub: crea el incidente y lo cierra solo si un probe posterior funciona. Se ejecuta al cambiar su workflow o la lógica de alertas en main, y manualmente. Consultar [sus runs](https://github.com/gusbakers/max1102-pipeline/actions/workflows/monitor-drill.yml) para la evidencia; un workflow meramente definido no cuenta como simulacro aprobado.

No se han ejecutado desde esta terminal imports/applies cloud, despliegues autenticados, consultas de facturación ni una presentación al equipo. No hay credenciales locales para esos proveedores.
