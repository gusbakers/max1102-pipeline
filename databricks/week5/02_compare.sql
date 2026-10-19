-- Databricks SQL: compares only months present in the legacy report.
-- Run after the same raw snapshot has been processed by both implementations.
WITH months AS (
  SELECT DISTINCT report_month FROM workspace.max1102_pipeline.report_monthly
), legacy AS (
  SELECT specialty, report_month, claim_count, total_amount
  FROM workspace.max1102_pipeline.report_monthly
), migrated AS (
  SELECT specialty, report_month, claim_count, total_amount
  FROM workspace.max1102_week5.report_monthly WHERE report_month IN (SELECT report_month FROM months)
)
SELECT 'legacy_only' AS difference, * FROM (SELECT * FROM legacy EXCEPT ALL SELECT * FROM migrated)
UNION ALL
SELECT 'dbt_only' AS difference, * FROM (SELECT * FROM migrated EXCEPT ALL SELECT * FROM legacy);
-- Expected: zero rows. This alone does NOT certify claims-level equivalence.

SELECT 'legacy_only' AS difference, * FROM (
  SELECT claim_id, member_id, provider_id, service_date, claim_status, claim_amount
  FROM workspace.max1102_pipeline.claims
  EXCEPT ALL
  SELECT claim_id, member_id, provider_id, service_date, claim_status, claim_amount
  FROM workspace.max1102_week5.claims
)
UNION ALL
SELECT 'dbt_only' AS difference, * FROM (
  SELECT claim_id, member_id, provider_id, service_date, claim_status, claim_amount
  FROM workspace.max1102_week5.claims
  EXCEPT ALL
  SELECT claim_id, member_id, provider_id, service_date, claim_status, claim_amount
  FROM workspace.max1102_pipeline.claims
);
