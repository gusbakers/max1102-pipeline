-- Full snapshot rebuild: every source month, not only the current month.
select p.specialty, count(*) as claim_count,
       sum(c.claim_amount) as total_amount, c.service_month as report_month
from {{ ref('claims') }} c
join {{ ref('providers') }} p on c.provider_id = p.provider_id
where c.claim_status = 'PAID'
group by p.specialty, c.service_month
