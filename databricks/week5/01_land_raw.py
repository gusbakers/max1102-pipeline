# Databricks notebook source
# MAGIC %md
# MAGIC # Semana 5 — Snapshot de entrada para dbt
# MAGIC Lee los archivos originales del Volume en un esquema separado. No usa los helpers incompletos de Week 1.
# COMMAND ----------
import re
from pyspark.sql import functions as F

for name, default in {
    'catalog': 'workspace', 'source_schema': 'max1102_week5_raw',
    'raw_dir': '/Volumes/workspace/max1102_pipeline/raw',
    'raw_format': 'csv',
}.items():
    dbutils.widgets.text(name, default)
catalog = dbutils.widgets.get('catalog')
schema = dbutils.widgets.get('source_schema')
raw_dir = dbutils.widgets.get('raw_dir').rstrip('/')
raw_format = dbutils.widgets.get('raw_format')
if raw_format not in {'csv', 'parquet'}:
    raise ValueError('Use csv or parquet')
if not all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in [catalog, schema]):
    raise ValueError('Invalid catalog or schema')
if schema == 'max1102_pipeline' or not raw_dir.startswith('/Volumes/'):
    raise ValueError('Use a separate landing schema and a Volume path')
spark.sql(f'CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`')
# COMMAND ----------
for name, columns in {
    'claims': ['claim_id', 'member_id', 'provider_id', 'service_date', 'claim_status', 'claim_amount'],
    'providers': ['provider_id', 'provider_name', 'specialty'],
}.items():
    path = f'{raw_dir}/{name}.{raw_format}'
    frame = (spark.read.option('header', True).option('mode', 'FAILFAST').csv(path)
             if raw_format == 'csv' else spark.read.parquet(path))
    missing = set(columns) - set(frame.columns)
    if missing or not frame.take(1):
        raise ValueError(f'{name}: missing columns or empty source: {sorted(missing)}')
    # Preserve raw values. dbt owns normalization, rejection and deduplication.
    raw = frame.select([F.col(c).cast('string').alias(c) for c in columns])
    raw.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable(
        f'{catalog}.{schema}.{name}_raw')
    print(name, raw.count())
# COMMAND ----------
# MAGIC %md
# MAGIC El snapshot debe contener todos los meses que se quieren conservar. Ejecutar dbt después de que AMBAS tablas se hayan cargado; nunca cargar a la vez que dbt.
