-- Q4. Estimated occupancy and revenue (ESTIMATES, see docs/DATA_MODEL.md for formula and assumptions).
--   nights  = LEAST(255, ROUND(reviews_ltm / review_rate * GREATEST(min_nights_avg, avg_stay)))
--   revenue = nights * current listed price      (gross, indicative, not realised income)
-- Listings with zero reviews in the last 12 months get 0 nights: the model cannot see unreviewed stays.
-- Two views in one table: with and without zero-review listings, because "typical" depends on that choice.
SELECT n.district, d.room_type,
       COUNT(*)                                                       AS n_listings,
       ROUND(100.0 * COUNT(*) FILTER (WHERE f.number_of_reviews_ltm = 0) / COUNT(*), 1) AS zero_review_pct,
       ROUND(median(f.est_nights_base), 0)                            AS median_nights_base_all,
       ROUND(median(f.est_nights_base) FILTER (WHERE f.number_of_reviews_ltm > 0), 0) AS median_nights_base_reviewed,
       ROUND(median(f.est_revenue_low), 0)                            AS median_revenue_low_all,
       ROUND(median(f.est_revenue_base), 0)                           AS median_revenue_base_all,
       ROUND(median(f.est_revenue_high), 0)                           AS median_revenue_high_all,
       ROUND(median(f.est_revenue_base) FILTER (WHERE f.number_of_reviews_ltm > 0), 0) AS median_revenue_base_reviewed,
       ROUND(quantile_cont(f.est_revenue_base, 0.9), 0)               AS p90_revenue_base_all,
       ROUND(AVG(f.est_occupancy_rate_base) FILTER (WHERE f.number_of_reviews_ltm > 0), 3) AS mean_occ_rate_reviewed,
       ROUND(SUM(f.est_revenue_base) / 1e6, 2)                        AS total_est_revenue_base_meur
FROM mart.fact_listing f
JOIN mart.dim_listing d USING (listing_id)
JOIN mart.dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key
WHERE d.is_benchmark
GROUP BY 1, 2
HAVING COUNT(*) >= 10
ORDER BY total_est_revenue_base_meur DESC;
