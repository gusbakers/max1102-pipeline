# Validation and deployment scope

[Project overview](../README.md)

## Evidence

The [recorded CI run](https://github.com/gusbakers/max1102-pipeline/actions/runs/39306847180) completed successfully for commit `e42c09d5d6a6894c9f40a730ca6ba1ad50c382a0`. Its jobs cover the API, Docker-based Airflow DAG validation, dbt, actual Kafka/PostgreSQL integration services, operational tools and Terraform syntax/schema validation.

| Check | Evidence and interpretation |
|---|---|
| Source generator | [Generator](../data/generate_data.py) creates 50,100 synthetic claim records and 1,200 providers. This is input volume, not a throughput benchmark. |
| Transformation scope | [dbt models](../dbt/models) contain eight models. Column/model assertions plus three singular SQL tests define 16 data checks. |
| Fixed dbt fixture | 69 source rows reconcile to one exact duplicate, eight rejected records and 60 valid claims. The report has four specialty/month rows. |
| Known answers | The local verification harness compares every accepted claim and report total with expected values, repeats the build and checks unchanged results. |
| Failure isolation | Conflicting provider IDs and excessive rejection are introduced deliberately; the harness requires failed builds and unchanged published claims/report data. |
| API/RAG local suite | The recorded local validation reports 51 passing tests. Provider responses are mocked or intercepted; the SDK serialization is exercised. This is not an authenticated Gemini quality benchmark. |
| Integration | CI starts actual Kafka and PostgreSQL/pgvector services and tests indexing, retrieval, API behavior, broker acknowledgements and recovery. |

The dbt verification uses DuckDB and committed fixtures. Databricks execution requires a correctly configured warehouse, permissions and source snapshot. The workflow uploads verification output, dbt manifests and integration results as run artifacts.

## Operational evidence

The [monitor run](https://github.com/gusbakers/max1102-pipeline/actions/runs/39804515628) completed successfully on the same source commit. The [alert drill](https://github.com/gusbakers/max1102-pipeline/actions/runs/39191878734) exercises the GitHub incident lifecycle. A successful probe or drill does not establish an uptime percentage, historical reliability or model availability.

The deployment workflow can publish the tested API artifact and check `/health` plus the deployed commit via `/version`. Deployment flags and account configuration control these jobs; a skipped deployment is not proof of a live release.

## Activation requirements

| Component | Required evidence before calling it operational |
|---|---|
| Original Databricks notebooks | Export and review workspace sources, restore the helpers missing from `00_common.py`, and verify an end-to-end job. Notebook deployment is blocked until source review is complete. |
| dbt on Databricks | Load the intended snapshot, execute models using the real warehouse and permissions, and reconcile against the notebook outputs. |
| Airflow deployment | Configure the connection and job IDs, then verify a complete run on the intended host. Codespaces alone is not a permanent scheduler. |
| Live RAG | Index reference documents with valid provider credentials; measure retrieval and generated answers, including abstention cases. |
| Azure API | Configure persistent PostgreSQL access and secrets, deploy the tested artifact, and verify authenticated endpoints and deployed SHA. |
| Terraform | Adopt the intended resources with an authorized backend and confirm the reviewed plan. Configuration validation is not an infrastructure apply. |
| Costs | Supply billing exports for the measured period. No savings claim is made without a baseline and comparable actual costs. |

The Kafka pilot persists to PostgreSQL. Continuous Kafka-to-Delta delivery is not implemented. All public examples use synthetic claims; this repository does not establish regulatory certification or suitability for real patient data.
