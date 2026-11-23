-- Q9. Map-ready summary at Ortsteil (neighbourhood) level, benchmark listings only.
-- Join to neighbourhoods.geojson on `neighbourhood` (+ district). Small areas are kept but flagged: n < 20 = indicative only.
SELECT n.neighbourhood_key, n.district, n.neighbourhood,
       COUNT(*)                                                         AS n_listings,
       COUNT(*) >= 20                                                   AS is_reliable_sample,
       ROUND(median(f.price_eur), 1)                                    AS median_price,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.room_type = 'Entire home/apt') / COUNT(*), 1) AS entire_home_pct,
       ROUND(median(f.est_nights_base), 0)                              AS median_est_nights,
       ROUND(median(f.est_revenue_base), 0)                             AS median_est_revenue,
       ROUND(AVG(f.review_scores_rating), 2)                            AS mean_review_score,
       RANK() OVER (ORDER BY median(f.price_eur) DESC)                  AS price_rank
FROM mart.fact_listing f
JOIN mart.dim_listing d ON d.listing_id = f.listing_id
JOIN mart.dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key
WHERE d.is_benchmark
GROUP BY 1, 2, 3
ORDER BY n_listings DESC;
