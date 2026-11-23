-- Q7. Review-based demand trend by district: YTD (Jan-Aug) 2026 vs same period 2025 and 2024.
-- Uses YTD because 2026 is incomplete. RANK() on growth; LAG on the yearly series.
WITH y AS (
    SELECT n.district, year(r.review_date) AS yr, COUNT(*) AS reviews
    FROM {{ ref('stg_reviews') }} r
    JOIN {{ ref('dim_listing') }} l USING (listing_id)
    JOIN {{ ref('dim_neighbourhood') }} n ON n.neighbourhood_key = l.neighbourhood_key
    WHERE month(r.review_date) <= 8 AND year(r.review_date) BETWEEN 2023 AND 2026
    GROUP BY 1, 2
), g AS (
    SELECT *, LAG(reviews) OVER (PARTITION BY district ORDER BY yr) AS reviews_prev
    FROM y
)
SELECT district, yr AS year_ytd_aug, reviews, reviews_prev,
       ROUND(100.0 * (reviews / NULLIF(reviews_prev, 0) - 1), 1)                     AS yoy_pct,
       RANK() OVER (PARTITION BY yr ORDER BY reviews / NULLIF(reviews_prev, 0) DESC) AS growth_rank
FROM g WHERE reviews_prev IS NOT NULL
ORDER BY yr DESC, growth_rank
