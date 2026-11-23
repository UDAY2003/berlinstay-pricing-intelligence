-- fails (returns rows) if any estimate exceeds 255 nights or scenarios are out of order
select listing_id from {{ ref('fact_listing') }}
where est_nights_high > 255 or est_nights_low > est_nights_base or est_nights_base > est_nights_high
