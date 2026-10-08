import hashlib
import logging
import re
from datetime import date, timedelta

import pendulum

from airflow.providers.databricks.operators.databricks import (
    DatabricksRunNowOperator,
)
from airflow.sdk import (
    DAG,
    Param,
    get_current_context,
    task,
)


def request_token(
    run_id,
    task_id,
    try_number,
):
    value = (
        f"{run_id}:{task_id}:{try_number}"
    )

    return hashlib.sha256(
        value.encode()
    ).hexdigest()


def log_failure(context):
    ti = context["task_instance"]

    logging.error(
        "FALLO | dag=%s | task=%s | run=%s",
        ti.dag_id,
        ti.task_id,
        ti.run_id,
    )


with DAG(
    dag_id="max1102_monthly_claims_report",
    description=(
        "Reporte mensual de claims: "
        "Databricks + Delta + Airflow"
    ),
    start_date=pendulum.datetime(
        2025,
        1,
        1,
        tz="America/New_York",
    ),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "gustavo",
        "retries": 1,
        "retry_delay": timedelta(
            minutes=1
        ),
        "execution_timeout": timedelta(
            minutes=30
        ),
        "on_failure_callback": log_failure,
    },
    params={
        "month": Param(
            "2025-12",
            type="string",
            pattern=(
                r"^[0-9]{4}-(0[1-9]|1[0-2])$"
            ),
        ),
        "raw_dir": Param(
            "/Volumes/workspace/max1102_pipeline/raw",
            type="string",
            pattern=r"^/Volumes/.+",
        ),
    },
    user_defined_macros={
        "request_token": request_token
    },
    tags=[
        "claims",
        "databricks",
        "max1102",
    ],
) as dag:

    @task(
        task_id="prepare",
        retries=0,
    )
    def prepare_parameters():
        context = get_current_context()

        month = (
            context["params"]["month"]
            .strip()
        )

        raw_dir = (
            context["params"]["raw_dir"]
            .strip()
            .rstrip("/")
        )

        if not re.fullmatch(
            r"[0-9]{4}-(0[1-9]|1[0-2])",
            month,
        ):
            raise ValueError(
                "Mes inválido: usa YYYY-MM"
            )

        year, month_number = map(
            int,
            month.split("-"),
        )

        date(
            year,
            month_number,
            1,
        )

        date(
            year + (month_number == 12),
            month_number % 12 + 1,
            1,
        )

        if not raw_dir.startswith(
            "/Volumes/"
        ):
            raise ValueError(
                "raw_dir debe empezar "
                "por /Volumes/"
            )

        batch_id = hashlib.sha256(
            context["run_id"].encode()
        ).hexdigest()[:24]

        return {
            "month": month,
            "raw_dir": raw_dir,
            "batch_id": batch_id,
        }

    prepared = prepare_parameters()

    job_params = {
        "month": (
            "{{ ti.xcom_pull("
            "task_ids='prepare')['month'] }}"
        ),
        "raw_dir": (
            "{{ ti.xcom_pull("
            "task_ids='prepare')['raw_dir'] }}"
        ),
        "batch_id": (
            "{{ ti.xcom_pull("
            "task_ids='prepare')['batch_id'] }}"
        ),
    }

    def databricks_task(
        task_id,
        job_name,
        retries=1,
    ):
        return DatabricksRunNowOperator(
            task_id=task_id,
            job_name=job_name,
            databricks_conn_id=(
                "databricks_default"
            ),
            job_parameters=dict(
                job_params
            ),
            idempotency_token=(
                "{{ request_token("
                "run_id, task.task_id, "
                "ti.try_number) }}"
            ),
            wait_for_termination=True,
            deferrable=False,
            polling_period_seconds=30,
            retries=retries,
        )

    extract = databricks_task(
        "extract",
        "max1102_01_extract",
    )

    validate = databricks_task(
        "validate",
        "max1102_02_validate",
        retries=0,
    )

    transform = databricks_task(
        "transform",
        "max1102_03_transform",
    )

    load = databricks_task(
        "load",
        "max1102_04_load",
    )

    @task(
        task_id="notify",
        retries=0,
        trigger_rule="all_success",
    )
    def notify_success():
        context = get_current_context()
        ti = context["ti"]

        cfg = ti.xcom_pull(
            task_ids="prepare"
        )

        url = ti.xcom_pull(
            task_ids="load",
            key="run_page_url",
        )

        logging.info(
            "REPORTE PUBLICADO | "
            "mes=%s | batch=%s | "
            "Databricks=%s",
            cfg["month"],
            cfg["batch_id"],
            url,
        )

        return {
            "status": "success",
            "month": cfg["month"],
        }

    notified = notify_success()

    (
        prepared
        >> extract
        >> validate
        >> transform
        >> load
        >> notified
    )