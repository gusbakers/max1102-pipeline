# max1102-pipeline

# MAX-1102 Monthly Claims Pipeline

Pipeline de reporte mensual de claims por especialidad.

## Stack

- GitHub web.
- GitHub Codespaces.
- Docker y Docker Compose.
- Apache Airflow 3.2.0.
- Python 3.12 dentro de Airflow.
- Apache Airflow Databricks provider 7.11.0.
- Databricks Serverless.
- PySpark.
- Delta Lake.
- Databricks CLI.
- GitHub Actions.

## Flujo

prepare → extract → validate → transform → load → notify

- prepare valida los parámetros y crea el batch_id.
- extract lee los archivos Parquet.
- validate aplica controles de calidad y registra rechazos.
- transform crea las tablas limpias.
- load publica el reporte mensual.
- notify registra el éxito en los logs de Airflow.

## Parámetros

- month: mes del reporte, con formato YYYY-MM.
- raw_dir: ruta del Volume con los archivos de entrada.
- batch_id: identificador generado por Airflow.

## Datos de entrada

Volume:

/Volumes/workspace/max1102_pipeline/raw

Archivos de entrada del DAG:

- claims.parquet
- providers.parquet

El notebook 00_setup_raw convierte los CSV iniciales a Parquet.

## Reporte

Tabla:

workspace.max1102_pipeline.report_monthly

Columnas:

- specialty
- claim_count
- total_amount
- report_month

Solo incluye claims con estado PAID.

La carga reemplaza el mes solicitado y conserva los otros meses.

## Jobs de Databricks

- max1102_01_extract
- max1102_02_validate
- max1102_03_transform
- max1102_04_load

## Arranque

Después de configurar .env:

```bash
docker build -t max1102-airflow:3.2.0 airflow
docker compose up airflow-init
docker compose up -d
```

Abrir el puerto 8080 desde el panel Ports de Codespaces.

## Validación del DAG

```bash
docker run --rm \
  --entrypoint python \
  -e AIRFLOW__CORE__LOAD_EXAMPLES=False \
  -v "$PWD/airflow/dags:/opt/airflow/dags:ro" \
  -v "$PWD/tests:/opt/project/tests:ro" \
  max1102-airflow:3.2.0 \
  /opt/project/tests/check_dag.py
```

GitHub Actions ejecuta esta comprobación al actualizar main.

## Credenciales

- El perfil de Databricks CLI se configura con databricks configure.
- La conexión de Airflow se llama databricks_default.
- .env y las credenciales se excluyen de Git.

## Operación

El DAG se ejecuta manualmente y admite una ejecución activa.

Esperar a que termine antes de ejecutar los notebooks manualmente
o detener el entorno.

## Apagado

```bash
docker compose down
```

Después, detener el Codespace desde GitHub.

Para conservar el proyecto, hacer commit y push antes de eliminar
el Codespace.

## Semana 4: entrega y operación

[![CI](https://github.com/gusbakers/max1102-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/gusbakers/max1102-pipeline/actions/workflows/ci.yml)

La implementación de CI/CD, Terraform, observabilidad y demo está en las carpetas del proyecto. Seguir [la guía de lunes a viernes](docs/week4/README.md), [activación con sesiones del Codespace](docs/week4/activation.md), [estado verificable](docs/week4/status.md) y [recuperación](docs/week4/runbook.md).

CI prueba la API sin consumir Gemini, verifica el DAG en Docker y valida herramientas/Terraform. CD Azure se habilita después de configurar la identidad OIDC; comprueba health y el SHA desplegado. El monitor horario abre/cierra incidentes en GitHub. Los despliegues Databricks/Airflow y la adopción real de Terraform requieren la configuración y evidencia descritas en la guía.

Los notebooks operativos del workspace deben exportarse y revisarse: la copia actual de `00_common.py` no contiene todos los helpers que usan las tareas. El despliegue de notebooks se bloquea hasta completar esa revisión.

`MAX_Week4/` es material histórico. No reinstalar sus plantillas sobre esta implementación.
