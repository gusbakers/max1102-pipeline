# Databricks notebook source
# MAGIC %run ./00_common

# COMMAND ----------

cfg = settings()
raw_dir = cfg["raw_dir"]

sources = [
    ("claims", CLAIM_COLUMNS),
    ("providers", PROVIDER_COLUMNS),
]

for filename, columns in sources:
    source_path = f"{raw_dir}/{filename}.csv"
    target_path = f"{raw_dir}/{filename}.parquet"

    df = (
        spark.read
        .option("header", True)
        .option("mode", "FAILFAST")
        .csv(source_path)
    )

    require_columns(df, columns, filename)

    (
        df.select(*columns)
        .write
        .mode("overwrite")
        .parquet(target_path)
    )

    rows = spark.read.parquet(target_path).count()
    print(f"{filename}: {rows} filas")