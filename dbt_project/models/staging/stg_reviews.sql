-- review_id is NOT unique in the source (3,676 ids under 2+ listings). Keep one row per review (smallest listing_id).
select review_id, min(listing_id) as listing_id, min(review_date) as review_date,
       date_trunc('month', min(review_date))::date as review_month
from {{ source('raw', 'reviews') }}
group by review_id
