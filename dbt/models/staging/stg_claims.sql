-- Exact raw duplicates are removed BEFORE normalization, matching Week 1.
with distinct_raw as (
  select distinct claim_id, member_id, provider_id,
                  service_date, claim_status, claim_amount
  from {{ raw_claims_relation('claims') }}
)
select
  nullif(trim(cast(claim_id as string)), '') as claim_id,
  nullif(trim(cast(member_id as string)), '') as member_id,
  nullif(trim(cast(provider_id as string)), '') as provider_id,
  cast(service_date as string) as service_date_raw,
  cast(claim_amount as string) as claim_amount_raw,
  try_cast(service_date as date) as service_date,
  try_cast(claim_amount as decimal(18,2)) as claim_amount,
  upper(trim(cast(claim_status as string))) as claim_status
from distinct_raw
