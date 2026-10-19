# Viernes — Integración y demostración

## Bloque 1. Entender qué verifica CI

El workflow `MAX Pipeline CI-CD` mantiene las comprobaciones de Week 4 e incorpora `week5-dbt` y `week5-integration`. Los tres trabajos de CD esperan también estos dos checks. No se activan por sí solos los flags de despliegue ni se crean recursos de nube.

| Comprobación | Qué demuestra | Qué no demuestra |
| --- | --- | --- |
| API y RAG | Contratos, autenticación, errores, citas y serialización real del SDK con HTTP interceptado | Una llamada válida al modelo de tu cuenta |
| dbt local | Modelos SQL reales, resultados conocidos, conciliación, repetición y fallos de calidad | Ejecución Spark con tu Volume y permisos |
| pgvector real | SQL de similitud, aislamiento de colección/modelo, reindexado y conservación ante errores | Calidad semántica con embeddings reales |
| Kafka real | Confirmación del broker, almacenamiento, reinicio, replay y rechazos | Alta disponibilidad o continuidad Kafka → Databricks |
| DAG en Docker | Importación de ambos DAGs y dependencias | Que el Job nuevo exista o haya corrido en tu cuenta |

Los artefactos de CI incluyen documentación/resultados dbt y el XML de las pruebas de integración. Las pruebas usan entradas sintéticas y HTTP interceptado para Gemini; no requieren ni consumen claves reales.

## Bloque 2. Reproducir los checks

Pruebas de API desde su carpeta:

```bash
cd api
../.venv-week5/bin/python -m pytest -q
cd ..
.venv-week5/bin/python -m pytest week5/tests/test_contracts.py week4/tests -q
.venv-week5/bin/python -m week5.verify_dbt
node --test week4/tests/monitor_issue.test.js
```

Para las pruebas de integración en Codespaces, carga las variables locales e inicia Compose. Esas pruebas añaden y retiran sus propias filas y topics de prueba; nunca las apuntes a una base compartida productiva.

```bash
TEST_DATABASE_URL="$RAG_DATABASE_URL" RUN_KAFKA_INTEGRATION=1 \
  .venv-week5/bin/python -m pytest week5/tests/test_integration.py -q
```

Sin `TEST_DATABASE_URL` las pruebas de integración se omiten: un resultado skipped no es una validación del servicio. GitHub Actions exige ambos servicios y no omite esos casos.

## Bloque 3. Demostrar el flujo

1. **dbt:** muestra `dbt build`, el linaje, `quality_summary` y la comparación de claims/reportes. Explica que el destino inicial es el esquema separado y que la publicación es de snapshot completo.
2. **RAG:** muestra una pregunta de estado con fuente y cita. Después pregunta por qué se denegó un claim particular; la documentación no contiene ese motivo y la respuesta debe reconocerlo. Revisa también una pregunta fuera de alcance. Una cita existente no sustituye esta evaluación del contenido.
3. **Kafka:** publica eventos, consume y consulta las tablas. Muestra un replay con el mismo ID y comprueba que el conteo de eventos no aumenta. Explica por qué el offset se confirma después de la transacción.
4. **Operación:** muestra el CI del commit y las evidencias reales de la cuenta cuando estén disponibles. Identifica qué sigue pendiente antes de llamar a la semana cerrada.

## Bloque 4. Recuperación

Si falla dbt, revisa el modelo o test y los rechazos antes de volver a ejecutar. Mantén los consumidores en el esquema anterior hasta resolver la comparación. No ignores un fallo de calidad para conseguir un build verde.

Si falla el reindexado, la colección previa se conserva. Repara el proveedor o el documento y repite el indexado. Para volver al resumen sencillo en Azure puedes quitar `RAG_ENABLED=true`; el endpoint explícito `/claims/rag-summary` seguirá exigiendo sus dependencias.

Si falla el consumidor, corrige la conexión y reinícialo con el mismo grupo. PostgreSQL deduplica mensajes que se guardaron antes de una interrupción. Un conflicto de evento necesita revisión; no sobrescribe el contenido original.

## Bloque 5. Entrega y cierre

Conserva URLs de runs, commit, resultado de comparación, evaluación de retrieval y smoke de Azure en `week5/evidence/` o en el sistema privado de evidencias de tu equipo. El directorio se excluye de Git para evitar publicar archivos operativos accidentales. Los artefactos sintéticos de CI están en Actions durante su retención.

Revisa costos/cuotas y detén Compose, Codespaces y el cómputo de Databricks que hayas iniciado. Snowflake y S3 no necesitan estar encendidos para este piloto. No declares activación permanente de Azure mientras PostgreSQL dependa del Codespace.
