-- Q6b. Forward unavailability on event / holiday dates vs the same-month ordinary days.
-- Compares each event window to NON-event days of the same calendar months, to limit the seasonal confound.
WITH daily AS (
    SELECT dd.date, dd.month_start, dd.event_name, dd.event_is_indicative, dd.is_weekend, dd.is_summer,
           AVG((NOT fd.is_available)::INT) AS unavail
    FROM mart.fact_listing_day fd
    JOIN mart.dim_date dd USING (date_key)
    JOIN mart.dim_listing l USING (listing_id)
    WHERE l.is_benchmark GROUP BY ALL
), ev AS (
    SELECT event_name, MIN(date) AS start_date, MAX(date) AS end_date, BOOL_OR(event_is_indicative) AS window_is_indicative,
           ROUND(100 * AVG(unavail), 1) AS event_unavailable_pct,
           ARRAY_AGG(DISTINCT month_start) AS months
    FROM daily WHERE event_name IS NOT NULL GROUP BY event_name
)
SELECT e.event_name, e.start_date, e.end_date, e.window_is_indicative, e.event_unavailable_pct,
       ROUND(100 * (SELECT AVG(unavail) FROM daily d
                    WHERE d.event_name IS NULL AND list_contains(e.months, d.month_start)), 1) AS other_days_same_months_pct,
       ROUND(e.event_unavailable_pct - 100 * (SELECT AVG(unavail) FROM daily d
                    WHERE d.event_name IS NULL AND list_contains(e.months, d.month_start)), 1) AS uplift_pp
FROM ev e ORDER BY start_date;
