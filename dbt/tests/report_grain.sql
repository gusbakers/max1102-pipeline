select specialty, report_month from {{ ref('report_monthly') }}
group by specialty, report_month having count(*) > 1
