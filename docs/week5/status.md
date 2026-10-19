# Estado verificable — Semana 5

## Código implementado

- Ocho modelos dbt con fuentes reales de Databricks y fixtures locales separados.
- Dieciséis pruebas de datos dbt y un harness que verifica resultados conocidos, repetición y bloqueos de calidad.
- Indexado de documentos con Gemini Embeddings y búsqueda exacta en pgvector.
- Endpoint RAG autenticado, comprobación de citas y conmutación del endpoint de Week 2 mediante `RAG_ENABLED`.
- Productor Kafka, consumidor transaccional y cuarentena SQL de eventos inválidos.
- Job de Databricks renderizable con commit fijo y DAG manual de Airflow.
- CI con servicios reales de PostgreSQL/pgvector y Kafka; guía de lunes a viernes.

## Evidencia de esta entrega

La validación local de dbt obtuvo 69 entradas, 1 duplicado exacto, 8 rechazos y 60 claims válidos, con cuatro filas de reporte. Se verificaron respuestas conocidas, repetición idéntica y fallos intencionales por proveedor contradictorio y pérdida excesiva. Este resultado usa DuckDB y fixtures, no los datos del workspace.

Las 51 pruebas de API/RAG pasaron localmente. Las llamadas de Gemini fueron interceptadas o reemplazadas por respuestas de prueba; el SDK real sí se ejercita para comprobar su serialización. Los resultados finales de CI corresponden al commit del pull request y se consultan en [Actions](https://github.com/gusbakers/max1102-pipeline/actions/workflows/ci.yml).

## Activación pendiente en las cuentas

| Parte | Comprobación necesaria |
| --- | --- |
| Databricks | Cargar el snapshot correcto, ejecutar dbt con permisos/warehouse reales y comparar contra los notebooks operativos. |
| Airflow | Crear el Job `max_week5_claims_dbt` en Databricks y ejecutar el DAG con su conexión existente. |
| Gemini | Indexar con una clave válida, medir retrieval y comprobar respuestas reales, incluidas las que deben abstenerse. |
| Azure | Disponer de PostgreSQL persistente accesible, configurar el RAG, desplegar y ejecutar el smoke autenticado. |

El entorno de implementación tenía acceso al repositorio, pero no sesiones de Azure/Databricks, claves de Gemini ni Docker local. La integración con contenedores se valida en Actions. No se afirma que se hayan activado esos servicios en tus cuentas ni que haya una conexión continua Kafka → Delta. La semana se cierra operativamente cuando se conservan esas evidencias reales.
