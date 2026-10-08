# Databricks notebook source
# MAGIC %run ./00_common

# COMMAND ----------

cfg = settings()

assessed = read_stage(
    "claims_assessed",
    cfg["batch_id"],
)

providers = read_stage(
    "providers_validated",
    cfg["batch_id"],
)

clean = (
    assessed
    .filter("reject_reason IS NULL")
    .select(*CLAIM_COLUMNS)
    .withColumn(
        "service_month",
        F.date_format(
            "service_date",
            "yyyy-MM",
        ),
    )
)

n_clean = clean.count()
n_assessed = assessed.count()

n_rejected = (
    assessed
    .filter("reject_reason IS NOT NULL")
    .count()
)

if (
    n_clean == 0
    or n_clean + n_rejected != n_assessed
):
    raise ValueError(
        "No cuadra la conciliación de claims"
    )

n_distinct_ids = (
    clean
    .select("claim_id")
    .distinct()
    .count()
)

if n_distinct_ids != n_clean:
    raise ValueError(
        "Persisten claim_id duplicados"
    )

save_stage(
    clean,
    "claims",
    cfg["batch_id"],
    partition_by="service_month",
)

save_stage(
    providers,
    "providers",
    cfg["batch_id"],
)

spark.sql(
    f"ANALYZE TABLE {table('claims')} "
    "COMPUTE STATISTICS"
)

spark.sql(
    f"ANALYZE TABLE {table('providers')} "
    "COMPUTE STATISTICS"
)

print(
    "Transformación y conciliación OK:",
    n_clean,
    "claims",
)