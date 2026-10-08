from airflow.models import DagBag

bag = DagBag(
    dag_folder="/opt/airflow/dags",
    include_examples=False,
)

assert not bag.import_errors, (
    bag.import_errors
)

dag = bag.dags[
    "max1102_monthly_claims_report"
]

order = [
    "prepare",
    "extract",
    "validate",
    "transform",
    "load",
    "notify",
]

assert set(dag.task_ids) == set(order), (
    dag.task_ids
)

for previous, current in zip(
    order,
    order[1:],
):
    assert (
        dag.get_task(current)
        .upstream_task_ids
        == {previous}
    )

assert dag.max_active_runs == 1

assert (
    dag.get_task("notify").trigger_rule
    == "all_success"
)

for task_id in [
    "extract",
    "validate",
    "transform",
    "load",
]:
    assert (
        dag.get_task(task_id)
        .wait_for_termination
        is True
    )

print(
    "OK: DAG importable, seis tareas, "
    "dependencias y espera de "
    "Databricks correctas"
)