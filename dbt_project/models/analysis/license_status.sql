-- Q8. Registration/licence field status among active short-stay listings (descriptive only).
-- The raw `license` field is free text entered by hosts. This is NOT a compliance check and says nothing legal about any listing.
SELECT d.room_type, d.license_status,
       COUNT(*)                                                         AS n_listings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY d.room_type), 1) AS pct_of_room_type,
       ROUND(median(f.price_eur), 1)                                    AS median_price,
       ROUND(median(f.est_revenue_base), 0)                             AS median_est_revenue
FROM {{ ref('dim_listing') }} d JOIN {{ ref('fact_listing') }} f USING (listing_id)
WHERE d.is_benchmark
GROUP BY 1, 2 ORDER BY 1, n_listings DESC
