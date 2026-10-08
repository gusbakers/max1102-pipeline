# Databricks notebook source
import re
from datetime import date

from pyspark.sql import functions as F
from pyspark.sql.window import Window

CATALOG = "workspace"
SCHEMA = "max1102_pipeline"

CLAIM_COLUMNS = [
    "claim_id",
    "member_id",
    "provider_id",
    "service_date",
    "claim_status",
    "claim_amount",
]

PROVIDER_COLUMNS = [
    "provider_id",
    "provider_name",
    "specialty",
]


def settings():
    defaults = {
        "month": "2025-12",
        "raw_dir": "/Volumes/workspace/max1102_pipeline/raw",
        "batch_id": "manual",
    }

    for key, value in defaults.items():
        dbutils.widgets.text(key, value)

    return {
        key: dbutils.widgets.get(key)
        for key in defaults
    }


def require_columns(df, expected_columns, source_name):
    missing = [
        column
        for column in expected_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{source_name}: faltan columnas {missing}"
        )