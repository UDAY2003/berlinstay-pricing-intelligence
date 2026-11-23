-- Occupancy/revenue ESTIMATES. nights = LEAST(cap, ROUND(reviews_ltm / review_rate * GREATEST(min_nights_avg, avg_stay)))
-- revenue = nights * price_eur (gross, indicative). Assumptions come from the seed occupancy_assumptions.
with a as (
    select
        max(review_rate)      filter (where scenario = 'low')  as rr_low,  max(avg_stay_nights) filter (where scenario = 'low')  as st_low,
        max(review_rate)      filter (where scenario = 'base') as rr_base, max(avg_stay_nights) filter (where scenario = 'base') as st_base,
        max(review_rate)      filter (where scenario = 'high') as rr_high, max(avg_stay_nights) filter (where scenario = 'high') as st_high,
        max(max_nights) as cap
    from {{ ref('occupancy_assumptions') }}
)
select l.*,
    least(a.cap, round(l.number_of_reviews_ltm / a.rr_low  * greatest(coalesce(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_low)))  as nights_low,
    least(a.cap, round(l.number_of_reviews_ltm / a.rr_base * greatest(coalesce(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_base))) as nights_base,
    least(a.cap, round(l.number_of_reviews_ltm / a.rr_high * greatest(coalesce(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_high))) as nights_high
from {{ ref('int_listings_flagged') }} l cross join a
