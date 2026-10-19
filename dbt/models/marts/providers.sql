select provider_id, provider_name, specialty from {{ ref('stg_providers') }}
