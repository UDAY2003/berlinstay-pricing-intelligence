-- Q3. Multi-listing hosts: who supplies the market and do they earn differently?
-- Aggregated by host-size bucket only. No host is identified (host_key is a hash and is not output).
SELECT h.host_type_key, h.host_type,
       COUNT(DISTINCT l.host_key)                                AS hosts,
       COUNT(*)                                                  AS active_listings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)        AS share_of_listings_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE l.room_type = 'Entire home/apt') / COUNT(*), 1) AS entire_home_pct,
       ROUND(median(f.price_eur), 1)                             AS median_price,
       ROUND(median(f.est_nights_base), 0)                       AS median_est_nights,
       ROUND(median(f.est_revenue_base), 0)                      AS median_est_revenue,
       ROUND(100.0 * SUM(f.est_revenue_base) / SUM(SUM(f.est_revenue_base)) OVER (), 1) AS share_of_est_revenue_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE l.license_status = 'registration_number') / COUNT(*), 1) AS registration_number_pct
FROM mart.dim_listing l
JOIN mart.fact_listing f USING (listing_id)
JOIN mart.dim_host_type h ON h.host_type_key = l.host_type_key
WHERE l.is_benchmark
GROUP BY 1, 2 ORDER BY 1;
