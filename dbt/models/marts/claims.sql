select claim_id, member_id, provider_id, service_date, claim_status, claim_amount,
       {{ month_key('service_date') }} as service_month
from {{ ref('int_claims_assessed') }}
where reject_reason is null
