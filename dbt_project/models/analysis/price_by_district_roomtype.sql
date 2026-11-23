-- Q1. Price by district and room type (benchmark population: priced, short-stay, price 10-1000 EUR).
-- Window functions: RANK() orders districts by median price inside each room type.
WITH base AS (
    SELECT n.district, d.room_type, f.price_eur
    FROM {{ ref('fact_listing') }} f
    JOIN {{ ref('dim_listing') }} d USING (listing_id)
    JOIN {{ ref('dim_neighbourhood') }} n ON n.neighbourhood_key = d.neighbourhood_key
    WHERE d.is_benchmark
), agg AS (
    SELECT district, room_type,
           COUNT(*)                               AS n_listings,
           ROUND(median(price_eur), 1)            AS median_price,
           ROUND(quantile_cont(price_eur, 0.25), 1) AS p25_price,
           ROUND(quantile_cont(price_eur, 0.75), 1) AS p75_price,
           ROUND(AVG(price_eur), 1)               AS mean_price
    FROM base GROUP BY 1, 2
)
SELECT *,
       RANK() OVER (PARTITION BY room_type ORDER BY median_price DESC) AS price_rank_in_room_type,
       ROUND(median_price / median(median_price) OVER (PARTITION BY room_type), 2) AS price_index_vs_district_median,
       n_listings >= 30 AS is_reliable_sample   -- below 30 listings treat the median as indicative only
FROM agg
ORDER BY room_type, price_rank_in_room_type
