# Semana 4 — CI/CD, infraestructura y operación

El código de los cinco días está integrado en el repositorio. `MAX_Week4/` conserva el material original: su instalador se bloquea para evitar que sobrescriba esta implementación.

**Código implementado no significa infraestructura desplegada.** La activación requiere sesiones del propietario, recursos reales y evidencia de ejecución. Consulta [estado y pendientes](status.md).

| Día | Trabajo | Código principal | Criterio de cierre |
|---|---|---|---|
| Lunes | Pruebas automáticas | `.github/workflows/ci.yml`, `api/test_*.py`, `tests/check_dag.py`, `week4/tests/` | CI del commit en verde y checks obligatorios en main |
| Martes | Despliegue automático | `week4/scripts/azure_oidc.py`, `activate_from_terminal.py`, `deploy_notebooks.py`, `ops/airflow/` | API entrega el SHA probado; notebooks y host requieren su configuración real |
| Miércoles | Terraform | `infra/azure/`, `generate_infra.py`, `check_import_plan.py` | Recursos existentes importados, estado remoto y plan sin cambios |
| Jueves | Monitoreo, alertas y costos | `monitor.yml`, `api/week4_observability.py`, `cost_report.py` | Probe real, alerta y recuperación demostradas, costos con exportaciones reales |
| Viernes | Presentación y demo | [demo](../../week4/demo.md), [runbook](runbook.md) | Flujo completo demostrado y límites explicados con evidencia |

## Lunes — CI

Stack: Python 3.12, pytest, FastAPI, SDK de Google simulado, Docker/Airflow 3.2.0, GitHub Actions y Terraform 1.13.5.

1. Desde la raíz, instalar dependencias en un entorno aislado:

   ```bash
   python3 -m venv .venv-week4
   .venv-week4/bin/python -m pip install -r api/requirements-dev.txt -r week4/requirements-dev.txt
   ```

2. Ejecutar las pruebas. La API usa claves ficticias y transporte HTTP interceptado; no consume Gemini:

   ```bash
   (cd api && ../.venv-week4/bin/python -m pytest -q)
   .venv-week4/bin/python -m pytest week4/tests -q
   node --test week4/tests/monitor_issue.test.js
   python3 week4/scripts/package_api.py
   ```

   `release/api.zip` contiene solo `main.py`, `week4_observability.py`, `requirements.txt` y el SHA. Se excluyen `.env`, tests y dependencias de desarrollo.

3. GitHub Actions además construye la imagen real de Airflow y verifica sus seis tareas, orden y reintentos. Los notebooks reciben una comprobación de sintaxis; eso no verifica Spark ni Great Expectations dentro de Databricks.
4. Cada PR a main ejecuta `api-tests`, `check-dag`, `tooling-tests` y `terraform-validate`. En Settings → Rules/Branches, exigir esos checks y PR antes de integrar. Un workflow por sí solo no protege main. No activar CD hasta tener CI en verde.

## Martes — CD

Stack: GitHub Actions, Azure OIDC, Azure App Service existente, ZIP por commit. No se crea otro plan ni servidor.

1. En la terminal que ya tenga tus sesiones, ejecutar:

   ```bash
   python3 week4/scripts/check_access.py
   ```

   Este diagnóstico informa si funcionan las sesiones, sin imprimir tokens. La terminal de ChatGPT y el Codespace no comparten credenciales automáticamente.

2. Después de integrar a main y tener un CI verde, activar la API con el asistente de [activación](activation.md). Reutiliza `az` y `gh` autenticados; configura federación para main y permisos limitados a la Web App existente.
3. El job de CD descarga el ZIP del mismo workflow/commit, instala dependencias en Azure y exige `/health` correcto y `/version` igual al SHA probado. Si falla, el workflow queda rojo: no se considera un despliegue exitoso.
4. La API conserva `APP_API_KEY`, `GEMINI_API_KEY` y `GEMINI_MODEL` existentes en App Service. No se almacenan en el repositorio ni se necesitan para probar `/health`.
5. Databricks está bloqueado hasta exportar los notebooks operativos. El `00_common.py` actual del repositorio carece de `read_stage`, `save_stage`, `table` y los límites mensuales usados por otros notebooks. Ver [activación](activation.md). No activar su CD con estos archivos.
6. Airflow en Codespaces se detiene con el Codespace. El despliegue opcional por SSH requiere un host de laboratorio existente y una ventana aprobada por commit; no constituye alojamiento productivo permanente. [Operación del host](../../ops/airflow/README.md).

## Miércoles — Terraform

Stack: Terraform, proveedores Azure/AzureAD/AWS/Databricks/Snowflake y estado remoto en una organización HCP del propietario, si está disponible sin agregar servicios de pago.

1. Obtener identificadores reales con las sesiones existentes; completar `infra/inventory.json` a partir del ejemplo. No inventar un bucket, región ni Job ID.
2. Seguir [infra/README.md](../../infra/README.md): generar raíces por proveedor, obtener HCL desde recursos existentes y revisar valores sensibles.
3. Ejecutar `fmt`, `validate` y un plan guardado. `check_import_plan.py --require-import` permite importaciones/no-op y rechaza crear, actualizar, borrar o reemplazar recursos.
4. Aplicar exactamente ese plan de importación y comprobar después un plan vacío. Registrar direcciones, propietario, backend y evidencia sanitizada.
5. Activar drift de Azure solamente después de importar y configurar una identidad lectora. Los demás proveedores requieren configurar su autenticación y controles de drift; no se declaran cubiertos por el workflow de Azure.

`infra/azure/` es una definición de referencia validable sin acceso cloud. No es evidencia de importación. La raíz operativa elegida es `infra/adopted/azure/`; nunca administrar los mismos recursos con dos estados.

## Jueves — Monitoreo, alertas y costos

Stack: logs JSON, GitHub Actions programado, Issues y consultas/exportaciones de facturación.

1. El monitor consulta la API cada hora en el minuto 23 UTC y al cambiar main. Se puede ejecutar manualmente. Reintenta tres veces; el resultado incluye fecha y latencia. No envía datos de claims ni consume Gemini.
2. Una falla abre un incidente; fallas repetidas actualizan el mismo. La recuperación lo cierra con enlace a la evidencia. Configurar Watch/Notifications en GitHub para recibir avisos: crear un Issue no garantiza entrega de correo.
3. Ejecutar un simulacro desde Actions → MAX production monitor → Run workflow → `drill_mode=fail`, luego `recover`. El simulacro tiene su propio Issue y no detiene la API; la recuperación exige que el probe real funcione.
4. Opcionalmente activar monitoreo de los cuatro Jobs con IDs y credenciales reales. Un fallo reciente se alerta aunque haya una ejecución exitosa anterior. La antigüedad máxima de 35 días corresponde al proceso mensual; no comprueba por sí sola la calidad/frescura de la tabla final.
5. Ver en Azure los logs JSON y métricas HTTP 5xx, solicitudes, tiempo de respuesta y CPU. `/health` comprueba disponibilidad básica; no demuestra que Gemini o la carga de datos funcionen. Revisar también la ejecución del DAG, rechazos de calidad y `report_month` en Delta.
6. Completar [costos](../../week4/costos.md) con datos exportados. El generador rechaza exportaciones vacías y separa monedas, créditos y DBU. No se atribuyen costos cero a servicios sin evidencia.

GitHub puede retrasar ejecuciones programadas y deshabilitar schedules de repositorios públicos sin actividad durante 60 días. Este monitor es útil para el laboratorio; no ofrece un SLA 24/7.

## Viernes — Presentación y demostración

1. Usar [week4/demo.md](../../week4/demo.md) como guion de 12–15 minutos: arquitectura del mes, calidad, API, entrega, infraestructura y costos.
2. Preparar datos sintéticos y evidencias sin credenciales ni datos personales. No provocar fallos reales en producción para demostrar alertas.
3. Mostrar PR → CI → artifact → CD → `/version` y una ejecución mensual exitosa, cuando el acceso real lo permita.
4. Enseñar el plan de Terraform sin cambios, incidente de simulacro y recuperación, revisión de costos y procedimiento de rollback.
5. Cerrar con pendientes explícitos. Una presentación de código no sustituye las verificaciones cloud pendientes.
