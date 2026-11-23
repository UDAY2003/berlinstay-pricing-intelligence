-- Grain: one row per listing. Descriptive attributes only.
select
    l.listing_id, n.neighbourhood_key, h.host_type_key, l.host_key,
    l.room_type, l.property_type, l.accommodates,
    case when l.accommodates <= 2 then '1-2' when l.accommodates <= 4 then '3-4'
         when l.accommodates <= 6 then '5-6' else '7+' end as capacity_band,
    l.bedrooms, l.beds, l.bathrooms, l.has_shared_bath, l.amenities_count,
    l.is_superhost, l.license_status,
    l.has_price, l.is_price_outlier, l.is_mid_term, l.is_benchmark,
    case when not l.has_price then 'No price (inactive/unbookable)'
         when l.is_mid_term then 'Mid-term (28+ nights)' else 'Short-stay' end as listing_segment,
    l.latitude, l.longitude
from {{ ref('int_listings_flagged') }} l
left join {{ ref('dim_neighbourhood') }} n on n.neighbourhood = l.neighbourhood and n.district = l.neighbourhood_group
left join {{ ref('dim_host_type') }} h on l.host_listings_count between h.min_listings and h.max_listings
