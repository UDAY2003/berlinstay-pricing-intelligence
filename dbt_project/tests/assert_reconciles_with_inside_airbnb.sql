-- fails if our base occupancy estimate matches Inside Airbnb's own column (within 1 night) for <= 97% of listings
select share from (
  select avg((abs(est_nights_base - ia_est_occupancy_nights) <= 1)::int) as share from {{ ref('fact_listing') }}
) where share <= 0.97
