-- DIMENSIONS (star schema). See docs/DATA_MODEL.md for grain and keys.
CREATE SCHEMA IF NOT EXISTS mart;

-- Grain: one row per Berlin Ortsteil (neighbourhood). Key: neighbourhood_key (surrogate).
CREATE OR REPLACE TABLE mart.dim_neighbourhood AS
SELECT row_number() OVER (ORDER BY neighbourhood_group, neighbourhood) AS neighbourhood_key,
       neighbourhood_group AS district, neighbourhood
FROM raw.neighbourhoods;

-- Grain: one row per host-size bucket (derived from calculated_host_listings_count).
CREATE OR REPLACE TABLE mart.dim_host_type AS
SELECT * FROM (VALUES
    (1, 'Single-listing host',   1,  1),
    (2, 'Small multi (2-3)',     2,  3),
    (3, 'Professional (4-10)',   4, 10),
    (4, 'Commercial (11+)',     11, 100000)
) t(host_type_key, host_type, min_listings, max_listings);

-- Grain: one row per calendar day 2009-01-01 .. 2027-12-31. Key: date_key (yyyymmdd int).
CREATE OR REPLACE TABLE mart.dim_date AS
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER)          AS date_key,
    d::DATE                                         AS date,
    year(d)                                         AS year,
    quarter(d)                                      AS quarter,
    month(d)                                        AS month,
    strftime(d, '%b')                               AS month_name,
    date_trunc('month', d)::DATE                    AS month_start,
    date_trunc('week', d)::DATE                     AS week_start,
    isodow(d)                                       AS iso_day_of_week,
    isodow(d) >= 6                                  AS is_weekend,
    CASE WHEN month(d) IN (12,1,2) THEN 'Winter' WHEN month(d) IN (3,4,5) THEN 'Spring'
         WHEN month(d) IN (6,7,8) THEN 'Summer' ELSE 'Autumn' END AS season,
    month(d) IN (6,7,8)                             AS is_summer,
    (month(d) = 12 AND day(d) >= 20) OR (month(d) = 1 AND day(d) <= 2) AS is_christmas_window,
    e.event_name,
    COALESCE(e.is_indicative, FALSE)                AS event_is_indicative
FROM generate_series(DATE '2009-01-01', DATE '2027-12-31', INTERVAL 1 DAY) AS g(d)
LEFT JOIN ref.event_window e ON d::DATE BETWEEN e.start_date AND e.end_date;

-- Grain: one row per listing (current snapshot). Key: listing_id (natural, unique).
-- Descriptive attributes only; numeric measures live in fact_listing.
CREATE OR REPLACE TABLE mart.dim_listing AS
SELECT
    l.listing_id,
    n.neighbourhood_key,
    h.host_type_key,
    l.host_key,                         -- hashed host id; used for counting, never exported
    l.room_type,
    l.property_type,
    l.accommodates,
    CASE WHEN l.accommodates <= 2 THEN '1-2' WHEN l.accommodates <= 4 THEN '3-4'
         WHEN l.accommodates <= 6 THEN '5-6' ELSE '7+' END            AS capacity_band,
    l.bedrooms, l.beds, l.bathrooms, l.has_shared_bath, l.amenities_count,
    l.is_superhost,
    l.license_status,
    l.has_price, l.is_price_outlier, l.is_mid_term, l.is_benchmark,
    CASE WHEN NOT l.has_price THEN 'No price (inactive/unbookable)'
         WHEN l.is_mid_term THEN 'Mid-term (28+ nights)' ELSE 'Short-stay' END AS listing_segment,
    l.latitude, l.longitude
FROM stg.listings l
LEFT JOIN mart.dim_neighbourhood n
       ON n.neighbourhood = l.neighbourhood AND n.district = l.neighbourhood_group
LEFT JOIN mart.dim_host_type h
       ON l.host_listings_count BETWEEN h.min_listings AND h.max_listings;
