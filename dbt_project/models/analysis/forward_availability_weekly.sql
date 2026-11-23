-- Q6a. Forward calendar: share of ACTIVE short-stay listings NOT available per week (2026-09-19 .. 2027-09-19).
-- 'Unavailable' = booked OR blocked by the host; the calendar cannot separate them. Read as booking pressure, not occupancy.
-- Window functions: LAG for week-on-week change, RANK across the 53 weeks.
WITH w AS (
    SELECT dd.week_start,
           MIN(dd.date)                                            AS first_day_in_data,
           COUNT(*)                                                AS listing_days,
           ROUND(100.0 * AVG((NOT fd.is_available)::INT), 1)       AS unavailable_pct,
           MAX(dd.event_name)                                      AS event_name   -- one label per week, if any
    FROM {{ ref('fact_listing_day') }} fd
    JOIN {{ ref('dim_date') }} dd USING (date_key)
    JOIN {{ ref('dim_listing') }} l USING (listing_id)
    WHERE l.is_benchmark
    GROUP BY dd.week_start
)
SELECT week_start, first_day_in_data, listing_days, unavailable_pct, event_name,
       ROUND(unavailable_pct - LAG(unavailable_pct) OVER (ORDER BY week_start), 1) AS wow_change_pp,
       RANK() OVER (ORDER BY unavailable_pct DESC) AS busiest_rank
FROM w ORDER BY week_start
