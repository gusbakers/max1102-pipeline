"""Manual shadow-schema migration. Databricks executes landing followed by real dbt."""
import logging
import hashlib
from datetime import timedelta
import pendulum
from airflow.sdk import DAG, get_current_context, task
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator


def dbt_request_token(run_id):
    return hashlib.sha256(run_id.encode()).hexdigest()


with DAG(
    dag_id='max_week5_claims_dbt', schedule=None,
    start_date=pendulum.datetime(2026, 10, 19, tz='America/New_York'),
    catchup=False, max_active_runs=1,
    user_defined_macros={'dbt_request_token':dbt_request_token},
    default_args={'owner':'gustavo', 'retries':0,
                  'retry_delay':timedelta(minutes=1), 'execution_timeout':timedelta(minutes=35)},
    tags=['claims','dbt','week5'],
) as dag:
    build = DatabricksRunNowOperator(
        task_id='dbt_build', job_name='max_week5_claims_dbt',
        databricks_conn_id='databricks_default', wait_for_termination=True,
        polling_period_seconds=30, deferrable=False,
        idempotency_token='{{ dbt_request_token(run_id) }}',
    )

    @task(task_id='notify', trigger_rule='all_success')
    def notify():
        context = get_current_context()
        url = context['ti'].xcom_pull(task_ids='dbt_build', key='run_page_url')
        logging.info('DBT BUILD SUCCESS | schema=workspace.max1102_week5 | run=%s', url)
        return {'schema':'workspace.max1102_week5','run_page_url':url}

    build >> notify()
