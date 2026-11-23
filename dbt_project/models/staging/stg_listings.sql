-- Typed, renamed, one row per source row. Privacy: name/description/host_name/urls/pictures are NOT selected;
-- license text is reduced to a category; host id is hashed.
select
    id                                              as listing_id,
    md5(cast(host_id as varchar))                   as host_key,
    neighbourhood_group_cleansed                    as neighbourhood_group,
    neighbourhood_cleansed                          as neighbourhood,
    room_type,
    property_type,
    accommodates,
    bedrooms,
    beds,
    case when lower(bathrooms_text) like '%half%' then 0.5
         else try_cast(regexp_extract(bathrooms_text, '([0-9]+\.?[0-9]*)', 1) as double) end as bathrooms,
    coalesce(lower(bathrooms_text) like '%shared%', false) as has_shared_bath,
    try_cast(replace(replace(price, '$', ''), ',', '') as double) as price_raw,
    minimum_nights,
    maximum_nights,
    minimum_nights_avg_ntm,
    has_availability,
    availability_30, availability_60, availability_90, availability_365,
    number_of_reviews, number_of_reviews_ltm, number_of_reviews_l30d,
    first_review, last_review, reviews_per_month,
    review_scores_rating, review_scores_cleanliness, review_scores_location, review_scores_value,
    coalesce(host_is_superhost, false)              as is_superhost,
    calculated_host_listings_count                  as host_listings_count,
    calculated_host_listings_count_entire_homes     as host_entire_homes_count,
    calculated_host_listings_count_private_rooms    as host_private_rooms_count,
    case when license is null                                  then 'missing'
         when regexp_matches(license, '^[0-9]{2}[/-][Zz][/-]') then 'registration_number'
         when license ilike 'Exempt%'                          then 'exempt'
         when license ilike 'Legal entity%'                    then 'legal_entity_stated'
         when license ilike 'First name%'                      then 'person_stated'
         else 'other_format' end                               as license_status,
    try(json_array_length(amenities::json))         as amenities_count,
    latitude, longitude,
    estimated_occupancy_l365d                       as ia_est_occupancy_nights,
    estimated_revenue_l365d                         as ia_est_revenue,
    last_scraped
from {{ source('raw', 'listings') }}
