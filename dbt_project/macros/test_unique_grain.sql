{% test dbt_utils_free_unique_grain(model) %}
{# composite grain checks, implemented per model below #}
{%- set grain = {'fact_listing_day': ['listing_id','date_key'], 'fact_review_month': ['listing_id','month_start']} -%}
select 1 from {{ model }} group by {{ grain.get(model.name, ['1'])|join(', ') }} having count(*) > 1
{% endtest %}
