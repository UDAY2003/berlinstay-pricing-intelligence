-- Q5b. Seasonal index of reviews by calendar month, from the 3 full post-COVID years 2023-2025.
-- index = month's share of the year / (1/12). 1.00 = average month, 1.20 = 20% above average.
-- Reviews are posted AFTER the stay, so the true demand peak is typically about a month earlier than the review peak.
WITH m AS (
    SELECT year(review_month) AS yr, month(review_month) AS mth, COUNT(*) AS reviews
    FROM stg.reviews WHERE year(review_month) BETWEEN 2023 AND 2025 GROUP BY 1, 2
), s AS (
    SELECT *, reviews * 1.0 / SUM(reviews) OVER (PARTITION BY yr) AS year_share FROM m
)
SELECT mth AS month, strftime(make_date(2000, mth, 1), '%b') AS month_name,
       ROUND(AVG(year_share) * 12, 2)                 AS seasonal_index,
       RANK() OVER (ORDER BY AVG(year_share) DESC)    AS rank_busiest,
       ROUND(MIN(year_share) * 12, 2)                 AS index_min_year,
       ROUND(MAX(year_share) * 12, 2)                 AS index_max_year
FROM s GROUP BY mth ORDER BY mth;
