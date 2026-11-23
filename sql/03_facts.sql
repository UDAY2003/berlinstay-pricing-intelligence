-- FACTS (star schema).

-- Grain: one row per listing (snapshot 2026-09-19). Key: listing_id -> dim_listing.
-- Measures: price, availability, review counts, estimated occupancy nights and revenue (low/base/high).
-- Occupancy formula (ESTIMATE): nights = LEAST(cap, ROUND(reviews_ltm / review_rate * GREATEST(min_nights_avg, avg_stay)))
-- Revenue formula (ESTIMATE):   revenue = nights * current listed price   (gross, before fees/taxes/cleaning,
--                                uses today's price for the past 12 months, so it is indicative, not realised income)
CREATE OR REPLACE TABLE mart.fact_listing AS
WITH a AS (
    SELECT
        MAX(review_rate)      FILTER (scenario='low')  AS rr_low,  MAX(avg_stay_nights) FILTER (scenario='low')  AS st_low,
        MAX(review_rate)      FILTER (scenario='base') AS rr_base, MAX(avg_stay_nights) FILTER (scenario='base') AS st_base,
        MAX(review_rate)      FILTER (scenario='high') AS rr_high, MAX(avg_stay_nights) FILTER (scenario='high') AS st_high,
        MAX(max_nights) AS cap
    FROM ref.occupancy_assumptions
), est AS (
    SELECT l.*,
        -- low  = higher review rate and shorter stay -> fewer estimated nights
        -- high = lower review rate                   -> more estimated nights (cap still applies)
        LEAST(a.cap, ROUND(l.number_of_reviews_ltm / a.rr_low  * GREATEST(COALESCE(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_low)))  AS nights_low,
        LEAST(a.cap, ROUND(l.number_of_reviews_ltm / a.rr_base * GREATEST(COALESCE(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_base))) AS nights_base,
        LEAST(a.cap, ROUND(l.number_of_reviews_ltm / a.rr_high * GREATEST(COALESCE(l.minimum_nights_avg_ntm, l.minimum_nights), a.st_high))) AS nights_high
    FROM stg.listings l CROSS JOIN a
)
SELECT
    est.listing_id,
    d.neighbourhood_key,
    d.host_type_key,
    CAST(strftime(DATE '2026-09-19', '%Y%m%d') AS INTEGER) AS snapshot_date_key,
    price_eur,
    price_raw,
    minimum_nights, maximum_nights, minimum_nights_avg_ntm,
    availability_30, availability_60, availability_90, availability_365,
    number_of_reviews, number_of_reviews_ltm, number_of_reviews_l30d, reviews_per_month,
    first_review, last_review,
    review_scores_rating, review_scores_cleanliness, review_scores_location, review_scores_value,
    nights_low  AS est_nights_low,
    nights_base AS est_nights_base,
    nights_high AS est_nights_high,
    ROUND(nights_base / 365.0, 4)                  AS est_occupancy_rate_base,
    ROUND(nights_low  * price_eur, 0)              AS est_revenue_low,
    ROUND(nights_base * price_eur, 0)              AS est_revenue_base,
    ROUND(nights_high * price_eur, 0)              AS est_revenue_high,
    ia_est_occupancy_nights, ia_est_revenue
FROM est
JOIN mart.dim_listing d USING (listing_id);

-- Grain: one row per listing per future day (2026-09-19 .. 2027-09-19). Keys: listing_id, date_key.
-- is_available = FALSE means booked OR blocked by the host: the calendar cannot tell them apart.
CREATE OR REPLACE TABLE mart.fact_listing_day AS
SELECT listing_id,
       CAST(strftime(cal_date, '%Y%m%d') AS INTEGER) AS date_key,
       is_available, minimum_nights
FROM stg.calendar;

-- Grain: one row per listing per month with at least one review. Keys: listing_id, month_start.
-- Demand proxy only: a review is a lower bound of a stay.
CREATE OR REPLACE TABLE mart.fact_review_month AS
SELECT listing_id, review_month AS month_start, COUNT(*) AS n_reviews
FROM stg.reviews
GROUP BY 1, 2;

-- Grain: one row per week x neighbourhood x room type, benchmark listings only (aggregated from fact_listing_day).
-- Small enough for Power BI; the 4.5M-row daily table stays in DuckDB.
CREATE OR REPLACE TABLE mart.fact_availability_week AS
SELECT dd.week_start,
       d.neighbourhood_key,
       d.room_type,
       COUNT(*)                          AS listing_days,
       COUNT(*) FILTER (WHERE NOT fd.is_available) AS unavailable_days
FROM mart.fact_listing_day fd
JOIN mart.dim_date dd USING (date_key)
JOIN mart.dim_listing d USING (listing_id)
WHERE d.is_benchmark
GROUP BY 1, 2, 3;
