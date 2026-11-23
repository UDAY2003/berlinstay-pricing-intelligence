-- Grain: week x neighbourhood x room type, benchmark listings only. Small aggregate for Power BI.
select dd.week_start, d.neighbourhood_key, d.room_type,
       count(*) as listing_days,
       count(*) filter (where not fd.is_available) as unavailable_days
from {{ ref('fact_listing_day') }} fd
join {{ ref('dim_date') }} dd using (date_key)
join {{ ref('dim_listing') }} d using (listing_id)
where d.is_benchmark
group by 1, 2, 3
