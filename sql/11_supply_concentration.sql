-- Q2. Supply concentration: how is active supply spread across districts, and how concentrated is it?
-- Uses ALL priced listings (active supply), mid-term included but shown separately.
WITH d AS (
    SELECT n.district,
           COUNT(*)                                             AS active_listings,
           COUNT(*) FILTER (WHERE l.room_type = 'Entire home/apt') AS entire_homes,
           COUNT(*) FILTER (WHERE l.is_mid_term)                AS mid_term_listings
    FROM mart.dim_listing l JOIN mart.dim_neighbourhood n ON n.neighbourhood_key = l.neighbourhood_key
    WHERE l.has_price GROUP BY 1
), s AS (
    SELECT *, ROUND(100.0 * active_listings / SUM(active_listings) OVER (), 2) AS share_pct
    FROM d
)
SELECT district, active_listings, share_pct,
       RANK() OVER (ORDER BY active_listings DESC)                                  AS supply_rank,
       ROUND(SUM(share_pct) OVER (ORDER BY active_listings DESC), 2)                AS cumulative_share_pct,
       ROUND(100.0 * entire_homes / active_listings, 1)                             AS entire_home_pct,
       ROUND(100.0 * mid_term_listings / active_listings, 1)                        AS mid_term_pct,
       ROUND(SUM(POWER(share_pct, 2)) OVER (), 0)                                   AS city_hhi_districts  -- Herfindahl index, 0-10,000
FROM s ORDER BY supply_rank;
