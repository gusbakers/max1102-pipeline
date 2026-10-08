# Databricks notebook source
# MAGIC %run ./00_common

# COMMAND ----------

cfg = settings()

claims = read_stage(
    "claims_raw",
    cfg["batch_id"],
)

providers = read_stage(
    "providers_raw",
    cfg["batch_id"],
)

require_columns(
    claims,
    CLAIM_COLUMNS,
    "claims",
)

require_columns(
    providers,
    PROVIDER_COLUMNS,
    "providers",
)

claims = claims.select(*CLAIM_COLUMNS)
providers = providers.select(*PROVIDER_COLUMNS)

providers_ok = (
    providers.select(
        [
            F.trim(
                F.col(column).cast("string")
            ).alias(column)
            for column in PROVIDER_COLUMNS
        ]
    )
    .dropDuplicates()
)

bad_providers = providers_ok.filter(
    F.col("provider_id").isNull()
    | (F.col("provider_id") == "")
    | F.col("specialty").isNull()
    | (F.col("specialty") == "")
)

if bad_providers.limit(1).count():
    raise ValueError(
        "providers: ID o specialty vacíos"
    )

conflicting_providers = (
    providers_ok
    .groupBy("provider_id")
    .count()
    .filter("count > 1")
)

if conflicting_providers.limit(1).count():
    raise ValueError(
        "providers: un mismo ID tiene "
        "información contradictoria"
    )

n_raw = claims.count()

unique = claims.dropDuplicates()
n_unique = unique.count()
n_exact_dups = n_raw - n_unique

provider_keys = (
    providers_ok
    .select("provider_id")
    .withColumn(
        "_provider_ok",
        F.lit(True),
    )
)

staged = (
    unique
    .withColumn(
        "service_date_raw",
        F.col("service_date").cast("string"),
    )
    .withColumn(
        "claim_amount_raw",
        F.col("claim_amount").cast("string"),
    )
    .withColumn(
        "claim_id",
        F.trim(
            F.col("claim_id").cast("string")
        ),
    )
    .withColumn(
        "member_id",
        F.trim(
            F.col("member_id").cast("string")
        ),
    )
    .withColumn(
        "provider_id",
        F.trim(
            F.col("provider_id").cast("string")
        ),
    )
    .withColumn(
        "service_date",
        F.expr(
            "try_cast(service_date AS DATE)"
        ),
    )
    .withColumn(
        "claim_amount",
        F.expr(
            "try_cast(claim_amount AS DECIMAL(18,2))"
        ),
    )
    .withColumn(
        "claim_status",
        F.upper(
            F.trim(
                F.col("claim_status").cast("string")
            )
        ),
    )
    .join(
        F.broadcast(provider_keys),
        "provider_id",
        "left",
    )
    .withColumn(
        "reject_reason",
        F.when(
            F.col("claim_id").isNull()
            | (F.col("claim_id") == ""),
            "CLAIM_ID_NULO",
        )
        .when(
            F.col("member_id").isNull()
            | (F.col("member_id") == ""),
            "MEMBER_NULO",
        )
        .when(
            F.col("service_date").isNull(),
            "FECHA_INVALIDA",
        )
        .when(
            F.col("claim_amount").isNull(),
            "MONTO_INVALIDO",
        )
        .when(
            F.col("claim_amount") < 0,
            "MONTO_NEGATIVO",
        )
        .when(
            F.col("claim_status").isNull()
            | ~F.col("claim_status").isin(
                "PAID",
                "DENIED",
            ),
            "ESTADO_NO_ADMITIDO",
        )
        .when(
            F.col("_provider_ok").isNull(),
            "PROVEEDOR_INEXISTENTE",
        ),
    )
    .drop("_provider_ok")
)

window = (
    Window
    .partitionBy("claim_id")
    .orderBy(
        F.col("service_date").desc(),
        F.col("claim_amount").desc(),
        "provider_id",
        "member_id",
        "claim_status",
        "service_date_raw",
        "claim_amount_raw",
    )
)

ranked = (
    staged
    .filter("reject_reason IS NULL")
    .withColumn(
        "_rn",
        F.row_number().over(window),
    )
)

ranked_assessed = (
    ranked
    .withColumn(
        "reject_reason",
        F.when(
            F.col("_rn") > 1,
            "CLAIM_ID_DUPLICADO",
        ),
    )
    .drop("_rn")
)

assessed = (
    staged
    .filter("reject_reason IS NOT NULL")
    .unionByName(ranked_assessed)
)

rejected = assessed.filter(
    "reject_reason IS NOT NULL"
)

save_stage(
    rejected,
    "rejected_claims",
    cfg["batch_id"],
)

counts = {
    row["reject_reason"]: row["count"]
    for row in (
        rejected
        .groupBy("reject_reason")
        .count()
        .collect()
    )
}

n_rejected = sum(counts.values())

loss_pct = (
    100
    * (n_exact_dups + n_rejected)
    / n_raw
)

errors = [
    reason
    for reason, count in counts.items()
    if 100 * count / n_raw > 5.0
]

if 100 * n_exact_dups / n_raw > 5.0:
    errors.append(
        "Más de 5% de duplicados exactos"
    )

if loss_pct > 15.0:
    errors.append(
        "Más de 15% de pérdida total"
    )

if n_unique - n_rejected <= 0:
    errors.append(
        "No quedan claims válidos"
    )

if errors:
    raise ValueError(
        f"Calidad fallida: {errors}; "
        "revisa rejected_claims"
    )

save_stage(
    assessed,
    "claims_assessed",
    cfg["batch_id"],
)

save_stage(
    providers_ok,
    "providers_validated",
    cfg["batch_id"],
)

print(
    {
        "raw": n_raw,
        "exact_duplicates": n_exact_dups,
        "rejected": n_rejected,
        "valid": n_unique - n_rejected,
        "loss_pct": round(loss_pct, 2),
        "reasons": counts,
    }
)