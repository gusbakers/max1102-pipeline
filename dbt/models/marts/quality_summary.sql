select
  (select count(*) from {{ raw_claims_relation('claims') }}) as raw_rows,
  (select count(*) from {{ raw_claims_relation('claims') }}) -
  (select count(*) from {{ ref('stg_claims') }}) as exact_duplicates,
  (select count(*) from {{ ref('rejected_claims') }}) as rejected_rows,
  (select count(*) from {{ ref('claims') }}) as valid_rows
