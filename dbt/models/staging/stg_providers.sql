select distinct
  nullif(trim(cast(provider_id as string)), '') as provider_id,
  trim(cast(provider_name as string)) as provider_name,
  nullif(trim(cast(specialty as string)), '') as specialty
from {{ raw_claims_relation('providers') }}
