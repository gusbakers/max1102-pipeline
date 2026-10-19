with expected as (
  select service_month, count(*) as n, sum(claim_amount) as amount
  from {{ ref('claims') }} where claim_status = 'PAID' group by service_month
), actual as (
  select report_month, sum(claim_count) as n, sum(total_amount) as amount
  from {{ ref('report_monthly') }} group by report_month
)
select * from expected e full outer join actual a on e.service_month = a.report_month
where e.n is null or a.n is null or e.n <> a.n or e.amount <> a.amount
