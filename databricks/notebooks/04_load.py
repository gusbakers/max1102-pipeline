# Databricks notebook source
# MAGIC %run ./00_common

# COMMAND ----------

cfg = settings()

claims = read_stage(
    "claims",
    cfg["batch_id"],
)

providers = read_stage(
    "providers",
    cfg["batch_id"],
)

claims.createOrReplaceTempView(
    "claims_ready"
)

providers.createOrReplaceTempView(
    "providers_ready"
)

query = f"""
SELECT /*+ BROADCAST(p) */
       p.specialty,
       COUNT(*) AS claim_count,
       SUM(c.claim_amount) AS total_amount
FROM claims_ready c
JOIN providers_ready p
  ON c.provider_id = p.provider_id
WHERE c.service_month = '{cfg["month"]}'
  AND c.service_date >= DATE '{cfg["start"]}'
  AND c.service_date < DATE '{cfg["end"]}'
  AND c.claim_status = 'PAID'
GROUP BY p.specialty
"""

report = (
    spark.sql(query)
    .withColumn(
        "report_month",
        F.lit(cfg["month"]),
    )
)

rows = report.collect()

if not rows:
    raise ValueError(
        "No hay claims pagados para "
        f"{cfg['month']}"
    )

expected = (
    claims
    .filter(
        (
            F.col("service_month")
            == cfg["month"]
        )
        & (
            F.col("claim_status")
            == "PAID"
        )
    )
    .count()
)

reported_claims = sum(
    row["claim_count"]
    for row in rows
)

if reported_claims != expected:
    raise ValueError(
        "El reporte no concilia con "
        "los claims pagados del mes"
    )

writer = (
    report.write
    .format("delta")
    .mode("overwrite")
)

if spark.catalog.tableExists(
    table("report_monthly")
):
    writer = writer.option(
        "replaceWhere",
        f"report_month = '{cfg['month']}'",
    )

writer.saveAsTable(
    table("report_monthly")
)

display(
    spark.table(
        table("report_monthly")
    )
    .filter(
        F.col("report_month")
        == cfg["month"]
    )
    .orderBy("specialty")
)

print(
    "Reporte publicado:",
    cfg["month"],
    "| claims:",
    expected,
)