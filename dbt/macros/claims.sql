{% macro raw_claims_relation(name) -%}
  {% if var('use_fixtures', false) %}{{ ref('fixture_' ~ name) }}
  {% else %}{{ source('landing', name ~ '_raw') }}{% endif %}
{%- endmacro %}

{% macro month_key(expression) -%}
  {% if target.type == 'duckdb' %}strftime({{ expression }}, '%Y-%m')
  {% else %}date_format({{ expression }}, 'yyyy-MM'){% endif %}
{%- endmacro %}

{% test claims_quality_limits(model) %}
with raw_count as (
  select count(*) as n from {{ raw_claims_relation('claims') }}
), assessed as (
  select count(*) as n,
         sum(case when reject_reason is null then 1 else 0 end) as valid
  from {{ model }}
), reasons as (
  select reject_reason, count(*) as n from {{ model }}
  where reject_reason is not null group by reject_reason
)
select 'empty_or_excessive_loss' as failure
from raw_count r cross join assessed a
where r.n = 0 or coalesce(a.valid, 0) = 0
   or 1.0 * (r.n - a.valid) / nullif(r.n, 0) > 0.15
   or 1.0 * (r.n - a.n) / nullif(r.n, 0) > 0.05
union all
select reject_reason from reasons cross join raw_count r
where 1.0 * reasons.n / nullif(r.n, 0) > 0.05
{% endtest %}
