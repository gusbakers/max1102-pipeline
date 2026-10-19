select * from {{ ref('int_claims_assessed') }} where reject_reason is not null
