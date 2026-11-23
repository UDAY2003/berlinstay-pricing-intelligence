-- Reference tables: modelling assumptions and event windows.
-- Everything an analyst might want to change lives here, not hidden inside queries.

CREATE SCHEMA IF NOT EXISTS ref;

-- Occupancy model: est_nights = LEAST(cap, reviews_ltm / review_rate * GREATEST(min_nights_avg, avg_stay))
--   review_rate : share of bookings that end in a public review (assumption)
--   avg_stay    : assumed average nights per booking (assumption)
--   cap         : max bookable nights per year (255 = 70% of 365, mirrors Inside Airbnb)
-- 'base' reproduces Inside Airbnb's own estimated_occupancy_l365d for 98.4% of listings (checked in tests);
-- low/high are OUR sensitivity bounds, not measurements.
CREATE OR REPLACE TABLE ref.occupancy_assumptions AS
SELECT * FROM (VALUES
    ('low',  0.60, 4.0, 255),
    ('base', 0.50, 6.3, 255),
    ('high', 0.40, 6.3, 255)
) t(scenario, review_rate, avg_stay_nights, max_nights);

-- Event windows. Dates verified against official sources on 2026-11-23 (see docs/DATA_MODEL.md, 'Event windows').
-- is_indicative = TRUE would mean 'not verified'; all current rows are verified. The window itself is OUR definition
-- (e.g. the Marathon weekend, Good Friday to Easter Monday), the dates are the source's.
CREATE OR REPLACE TABLE ref.event_window AS
SELECT * FROM (VALUES
    ('Berlin Marathon',      DATE '2026-09-26', DATE '2026-09-27', FALSE),
    ('Festival of Lights',   DATE '2026-10-09', DATE '2026-10-18', FALSE),
    ('Christmas / New Year', DATE '2026-12-20', DATE '2027-01-02', FALSE),
    ('Berlinale (film fest)',DATE '2027-02-10', DATE '2027-02-21', FALSE),
    ('Easter',               DATE '2027-03-26', DATE '2027-03-29', FALSE),
    ('ITB (travel fair)',    DATE '2027-03-16', DATE '2027-03-18', FALSE),
    ('Pride / CSD',          DATE '2027-07-24', DATE '2027-07-24', FALSE)
) t(event_name, start_date, end_date, is_indicative);
