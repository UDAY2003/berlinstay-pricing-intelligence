-- Grain: listing x month with >= 1 review (de-duplicated). Demand proxy only.
select listing_id, review_month as month_start, count(*) as n_reviews
from {{ ref('stg_reviews') }}
group by 1, 2
