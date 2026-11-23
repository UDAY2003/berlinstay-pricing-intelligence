-- STAGING: typed, cleaned, one row per source row. No business logic beyond cleaning.
-- Dropped on purpose (privacy): name, description, host_name, host_about, urls, pictures, review comments.
-- license text is reduced to a category because it can contain private persons' names.

CREATE SCHEMA IF NOT EXISTS stg;

CREATE OR REPLACE TABLE stg.listings AS
WITH base AS (
    SELECT
        id                                              AS listing_id,
        md5(CAST(host_id AS VARCHAR))                   AS host_key,          -- hashed, never exported
        neighbourhood_group_cleansed                    AS neighbourhood_group,
        neighbourhood_cleansed                          AS neighbourhood,
        room_type,
        property_type,
        accommodates,
        bedrooms,
        beds,
        -- bathrooms: parse text such as '1 bath', '1.5 baths', 'Half-bath', '1 shared bath'
        CASE WHEN lower(bathrooms_text) LIKE '%half%' THEN 0.5
             ELSE TRY_CAST(regexp_extract(bathrooms_text, '([0-9]+\.?[0-9]*)', 1) AS DOUBLE) END AS bathrooms,
        COALESCE(lower(bathrooms_text) LIKE '%shared%', FALSE) AS has_shared_bath,
        -- price: text like '$97.00' (currency is EUR, '$' is just Inside Airbnb formatting)
        TRY_CAST(replace(replace(price, '$', ''), ',', '') AS DOUBLE) AS price_raw,
        minimum_nights,
        maximum_nights,
        minimum_nights_avg_ntm,
        has_availability,
        availability_30, availability_60, availability_90, availability_365,
        number_of_reviews, number_of_reviews_ltm, number_of_reviews_l30d,
        first_review, last_review, reviews_per_month,
        review_scores_rating, review_scores_cleanliness, review_scores_location, review_scores_value,
        COALESCE(host_is_superhost, FALSE)              AS is_superhost,
        calculated_host_listings_count                  AS host_listings_count,
        calculated_host_listings_count_entire_homes     AS host_entire_homes_count,
        calculated_host_listings_count_private_rooms    AS host_private_rooms_count,
        -- license -> category only (no raw text). 'regnr' = looks like a Berlin registration number.
        CASE WHEN license IS NULL                                    THEN 'missing'
             WHEN regexp_matches(license, '^[0-9]{2}[/-][Zz][/-]')   THEN 'registration_number'
             WHEN license ILIKE 'Exempt%'                            THEN 'exempt'
             WHEN license ILIKE 'Legal entity%'                      THEN 'legal_entity_stated'
             WHEN license ILIKE 'First name%'                        THEN 'person_stated'
             ELSE 'other_format' END                                 AS license_status,
        TRY(json_array_length(amenities::JSON))         AS amenities_count,
        latitude, longitude,
        estimated_occupancy_l365d                       AS ia_est_occupancy_nights,
        estimated_revenue_l365d                         AS ia_est_revenue,
        last_scraped
    FROM raw.listings
)
SELECT
    *,
    -- data-quality flags (kept, never silently dropped)
    price_raw IS NOT NULL                                             AS has_price,
    (price_raw IS NOT NULL AND (price_raw < 10 OR price_raw > 1000))  AS is_price_outlier,
    CASE WHEN price_raw BETWEEN 10 AND 1000 THEN price_raw END        AS price_eur,
    COALESCE(minimum_nights_avg_ntm, minimum_nights) >= 28            AS is_mid_term,
    -- BENCHMARK POPULATION: priced, short-stay, price not an outlier
    -- COALESCE: three-valued logic would give NULL (not FALSE) for unpriced listings; fixed after v1.0 (found by a dbt test)
    COALESCE(price_raw BETWEEN 10 AND 1000
        AND COALESCE(minimum_nights_avg_ntm, minimum_nights) < 28, FALSE) AS is_benchmark
FROM base;

CREATE OR REPLACE TABLE stg.calendar AS
SELECT listing_id, date AS cal_date, available AS is_available, minimum_nights, maximum_nights
FROM raw.calendar;

-- review_id is NOT unique in the source: 3,676 ids appear under 2+ listing_ids (about 6.6k extra rows, mostly 2026,
-- concentrated in a few dozen hosts, i.e. cloned/merged listings). A review is one stay, so we keep ONE row per review_id
-- (smallest listing_id, deterministic). Effect: Jan-Aug 2026 YoY growth is 15.4% instead of 18.4%.
CREATE OR REPLACE TABLE stg.reviews AS
SELECT review_id, MIN(listing_id) AS listing_id, MIN(review_date) AS review_date,
       date_trunc('month', MIN(review_date))::DATE AS review_month
FROM raw.reviews
GROUP BY review_id;
