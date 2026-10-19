# Lunes — Transformaciones de claims con dbt

## Bloque 1. Entender qué se migró

dbt organiza consultas SQL como modelos con dependencias explícitas mediante `ref()`. El motor de Databricks ejecuta el SQL; dbt no sustituye al motor ni a Airflow.

| Modelo | Responsabilidad |
| --- | --- |
| `stg_providers` | Normaliza proveedores; los IDs contradictorios hacen fallar sus pruebas. |
| `stg_claims` | Elimina duplicados exactos de las seis columnas heredadas, normaliza y convierte fechas y montos. |
| `int_claims_assessed` | Asigna el primer motivo de rechazo y decide entre IDs duplicados válidos. |
| `claims` | Publica una fila válida por claim y el mes de servicio. |
| `providers` | Publica proveedores normalizados. |
| `rejected_claims` | Conserva los rechazos y sus motivos. |
| `report_monthly` | Agrupa únicamente PAID por especialidad y mes. |
| `quality_summary` | Concilia entradas, duplicados exactos, rechazados y válidos. |

La migración conserva el contrato del notebook exportado: PAID/DENIED admitidos, montos no negativos, proveedor existente y deduplicación por fecha más reciente, monto mayor y desempates deterministas. PENDING continúa admitido en la API y rechazado en este batch. Si tu notebook operativo de Week 2 usa otras reglas, compara y acuerda ese contrato antes del cambio de consumidores.

Los límites heredados son 5% por motivo, 5% de duplicados exactos y 15% de pérdida total. Las pruebas de dbt bloquean los modelos dependientes cuando esos límites fallan. No se presenta esta suite como una ejecución de Great Expectations.

## Bloque 2. Ejecutar una prueba completa sin nube

Desde la raíz, usando el entorno de la preparación común:

```bash
.venv-week5/bin/python -m week5.verify_dbt
```

El script ejecuta dbt con DuckDB y datos sintéticos versionados: 69 entradas, 1 duplicado exacto, 8 rechazos y 60 claims válidos. Comprueba las 60 filas esperadas, los montos por especialidad/mes, una segunda ejecución idéntica y dos fallos intencionales de calidad. Al terminar restaura las entradas originales y genera documentación.

Resultado: `dbt/target/week5-verification.json`, `manifest.json`, `run_results.json` e `index.html`. Estas pruebas verifican reglas y resultados en DuckDB. La ejecución Spark/Databricks sigue siendo una comprobación aparte.

## Bloque 3. Ejecutar con los datos de tu Databricks

La copia antigua de `00_common.py` en GitHub está incompleta. Week 5 usa un notebook de carga independiente y conserva la versión antigua sin sobrescribir el notebook que tienes funcionando en la cuenta.

En Databricks, importa y ejecuta `databricks/week5/01_land_raw.py` como notebook. Sus widgets tienen estos valores iniciales:

| Widget | Valor |
| --- | --- |
| `catalog` | `workspace` |
| `source_schema` | `max1102_week5_raw` |
| `raw_dir` | `/Volumes/workspace/max1102_pipeline/raw` |
| `raw_format` | `csv` |

CSV corresponde a las fuentes identificadas en el proyecto. Si utilizas los Parquet preparados por `00_setup_raw`, selecciona `parquet`. El notebook carga **ambas** fuentes como tablas Delta en el esquema nuevo. No ejecutes la carga al mismo tiempo que dbt.

Instala el adaptador en un entorno separado en Codespaces:

```bash
python3.12 -m venv .venv-dbt
.venv-dbt/bin/python -m pip install -r dbt/requirements.txt
```

Configura `DATABRICKS_HOST` como hostname sin `https://`, `DATABRICKS_HTTP_PATH` con el HTTP Path del SQL warehouse y `DBT_ENV_SECRET_DATABRICKS_TOKEN` con un token vigente en la terminal o gestor de secretos. El nombre `DBT_ENV_SECRET_` permite a dbt ocultarlo en logs; el archivo `dbt/profiles.yml` solo contiene referencias a variables.

```bash
.venv-dbt/bin/dbt debug --project-dir dbt --profiles-dir dbt --target databricks
.venv-dbt/bin/dbt build --project-dir dbt --profiles-dir dbt --target databricks
```

El destino inicial es `workspace.max1102_week5`. El perfil `local` usa DuckDB y el perfil `databricks` usa el warehouse real; confirma el target en la salida. Para automatización por Job puedes usar el perfil que genera Databricks, sin introducir un token en el repositorio.

## Bloque 4. Comparar y activar la orquestación

Ejecuta `databricks/week5/02_compare.sql` en Databricks SQL. Debes procesar el mismo snapshot con la versión operativa anterior. La primera consulta compara reportes en los meses presentes en la tabla anterior y la segunda compara claims fila por fila. Esperado: cero diferencias en ambas. Un error de acceso o una tabla ausente no cuenta como una comparación aprobada.

Week 5 reconstruye el **snapshot completo de todos los meses disponibles**. No es una estrategia incremental que preserve meses que ya no estén en la entrada. Conserva la entrada completa, o diseña otra estrategia antes de cambiar la fuente a un solo mes.

Para crear el Job de Databricks desde Codespaces, obtén el ID del SQL warehouse en sus detalles de conexión y define `WEEK5_WAREHOUSE_ID` en esa terminal. Después:

```bash
mkdir -p week5/evidence
.venv-week5/bin/python -m week5.render_databricks_job \
  --warehouse-id "$WEEK5_WAREHOUSE_ID" --commit "$(git rev-parse HEAD)" \
  > week5/evidence/databricks-job.json
databricks jobs create --json @week5/evidence/databricks-job.json --profile MAX1102
```

Ejecuta `jobs create` una sola vez. El JSON crea `max_week5_claims_dbt`, sin horario, con máximo una ejecución activa y el código fijado al commit. Requiere SQL warehouse Pro/Serverless y permisos para ejecutar tareas Serverless. Tiene dos tareas: cargar el snapshot y ejecutar `dbt build` en orden. Si la cuenta no admite estas tareas, la ruta CLI anterior sigue disponible; no crees cómputo de pago para resolver una limitación de la edición.

El DAG nuevo de Airflow, `max_week5_claims_dbt`, invoca ese Job por nombre con `databricks_default`, espera su finalización y registra el éxito. El Job tiene que existir antes de disparar el DAG. Revisa el código fijado en el Job al actualizar la rama. El DAG mensual anterior continúa disponible; cambia consumidores al nuevo esquema solamente después de la comparación real. No cambies las tablas productivas por un resultado de fixtures.
