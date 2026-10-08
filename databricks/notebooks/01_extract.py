# Databricks notebook source
# MAGIC %run ./00_common

# COMMAND ----------

cfg = settings()

for source in ["claims", "providers"]:
    df = spark.read.parquet(
        f"{cfg['raw_dir']}/{source}.parquet"
    )

    if df.limit(1).count() == 0:
        raise ValueError(
            f"{source}: archivo vacío"
        )

    save_stage(
        df,
        f"{source}_raw",
        cfg["batch_id"],
    )

    print(
        source,
        "leído y guardado para",
        cfg["batch_id"],
    )