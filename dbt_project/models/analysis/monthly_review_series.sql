-- Q5a. Monthly review series (demand proxy) with YoY change and rolling averages.
-- Window functions: LAG (12 months back), AVG OVER ROWS BETWEEN (3m and 12m rolling).
-- Caveat: listings that left the platform before the scrape are absent -> early years are understated (survivorship).
WITH m AS (
    SELECT review_month AS month_start, COUNT(*) AS reviews
    FROM {{ ref('stg_reviews') }} GROUP BY 1
), full_range AS (
    SELECT month_start::DATE AS month_start
    FROM generate_series(DATE '2015-01-01', DATE '2026-08-01', INTERVAL 1 MONTH) g(month_start)   -- 2026-09 is partial
)
SELECT r.month_start,
       COALESCE(m.reviews, 0)                                                      AS reviews,
       LAG(COALESCE(m.reviews, 0), 12) OVER w                                      AS reviews_prev_year,
       ROUND(100.0 * (COALESCE(m.reviews, 0) / NULLIF(LAG(COALESCE(m.reviews, 0), 12) OVER w, 0) - 1), 1) AS yoy_pct,
       ROUND(AVG(COALESCE(m.reviews, 0)) OVER (w ROWS BETWEEN 2  PRECEDING AND CURRENT ROW), 0) AS rolling_3m,
       ROUND(AVG(COALESCE(m.reviews, 0)) OVER (w ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 0) AS rolling_12m
FROM full_range r LEFT JOIN m USING (month_start)
WINDOW w AS (ORDER BY r.month_start)
ORDER BY r.month_start
