with checked as (
  select c.*,
    case
      when c.claim_id is null then 'CLAIM_ID_NULO'
      when c.member_id is null then 'MEMBER_NULO'
      when c.service_date is null then 'FECHA_INVALIDA'
      when c.claim_amount is null then 'MONTO_INVALIDO'
      when c.claim_amount < 0 then 'MONTO_NEGATIVO'
      when c.claim_status is null or c.claim_status not in (
        {% for status in var('accepted_claim_statuses') %}
          '{{ status }}'{% if not loop.last %},{% endif %}
        {% endfor %}
      ) then 'ESTADO_NO_ADMITIDO'
      when p.provider_id is null then 'PROVEEDOR_INEXISTENTE'
    end as reject_reason
  from {{ ref('stg_claims') }} c
  left join {{ ref('stg_providers') }} p on c.provider_id = p.provider_id
), ranked as (
  select *, row_number() over (
    partition by claim_id
    order by service_date desc, claim_amount desc, provider_id, member_id,
             claim_status, service_date_raw, claim_amount_raw
  ) as rn
  from checked where reject_reason is null
)
select claim_id, member_id, provider_id, service_date_raw, claim_amount_raw,
       service_date, claim_amount, claim_status,
       case when rn > 1 then 'CLAIM_ID_DUPLICADO' end as reject_reason
from ranked
union all
select claim_id, member_id, provider_id, service_date_raw, claim_amount_raw,
       service_date, claim_amount, claim_status, reject_reason
from checked where reject_reason is not null
