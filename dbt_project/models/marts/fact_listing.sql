-- Grain: one row per listing (snapshot 2026-09-19). est_* columns are ESTIMATES (see int_listing_estimates).
select
    e.listing_id, d.neighbourhood_key, d.host_type_key,
    cast(strftime(date '2026-09-19', '%Y%m%d') as integer) as snapshot_date_key,
    e.price_eur, e.price_raw,
    e.minimum_nights, e.maximum_nights, e.minimum_nights_avg_ntm,
    e.availability_30, e.availability_60, e.availability_90, e.availability_365,
    e.number_of_reviews, e.number_of_reviews_ltm, e.number_of_reviews_l30d, e.reviews_per_month,
    e.first_review, e.last_review,
    e.review_scores_rating, e.review_scores_cleanliness, e.review_scores_location, e.review_scores_value,
    e.nights_low  as est_nights_low,
    e.nights_base as est_nights_base,
    e.nights_high as est_nights_high,
    round(e.nights_base / 365.0, 4)             as est_occupancy_rate_base,
    round(e.nights_low  * e.price_eur, 0)       as est_revenue_low,
    round(e.nights_base * e.price_eur, 0)       as est_revenue_base,
    round(e.nights_high * e.price_eur, 0)       as est_revenue_high,
    e.ia_est_occupancy_nights, e.ia_est_revenue
from {{ ref('int_listing_estimates') }} e
join {{ ref('dim_listing') }} d using (listing_id)
