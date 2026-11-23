"""Schema context sent to the LLM: table/column descriptions, business definitions and few-shot examples.
Only this static text and the user's question leave the machine. No row values are ever sent to the provider."""

ALLOWED_TABLES = ["dim_listing", "dim_neighbourhood", "dim_host_type", "dim_date",
                  "fact_listing", "fact_review_month", "fact_availability_week", "fact_price_gap"]

SCHEMA_DOC = """
DuckDB SQL dialect. Berlin short-term-rental data (Inside Airbnb scrape 2026-09-19). Tables (star schema):

dim_neighbourhood(neighbourhood_key INT PK, district VARCHAR, neighbourhood VARCHAR)   -- 12 districts (Bezirke), 139 neighbourhoods (Ortsteile)
  district values: 'Mitte','Friedrichshain-Kreuzberg','Pankow','Charlottenburg-Wilm.','Neukölln','Tempelhof - Schöneberg','Treptow - Köpenick','Lichtenberg','Steglitz - Zehlendorf','Reinickendorf','Spandau','Marzahn - Hellersdorf'
dim_host_type(host_type_key INT PK, host_type VARCHAR, min_listings INT, max_listings INT)
  host_type values: 'Single-listing host','Small multi (2-3)','Professional (4-10)','Commercial (11+)'
dim_listing(listing_id BIGINT PK (opaque id), neighbourhood_key INT FK, host_type_key INT FK, room_type VARCHAR, property_type VARCHAR,
  accommodates INT, capacity_band VARCHAR ('1-2','3-4','5-6','7+'), bedrooms INT, beds INT, bathrooms DOUBLE, has_shared_bath BOOL, amenities_count INT,
  is_superhost BOOL, license_status VARCHAR ('registration_number','exempt','legal_entity_stated','person_stated','other_format','missing'),
  has_price BOOL, is_price_outlier BOOL, is_mid_term BOOL, is_benchmark BOOL, listing_segment VARCHAR, latitude DOUBLE, longitude DOUBLE)
  room_type values: 'Entire home/apt','Private room','Shared room','Hotel room'
  listing_segment values: 'Short-stay','Mid-term (28+ nights)','No price (inactive/unbookable)'
fact_listing(listing_id FK, neighbourhood_key FK, host_type_key FK, price_eur DOUBLE (nightly, EUR; NULL if no/outlier price), minimum_nights, maximum_nights,
  minimum_nights_avg_ntm, availability_30, availability_60, availability_90, availability_365 (days available), number_of_reviews, number_of_reviews_ltm (last 12 months),
  number_of_reviews_l30d, reviews_per_month, first_review DATE, last_review DATE, review_scores_rating, review_scores_cleanliness, review_scores_location, review_scores_value,
  est_nights_low, est_nights_base, est_nights_high (ESTIMATED booked nights per year), est_occupancy_rate_base (est_nights_base/365),
  est_revenue_low, est_revenue_base, est_revenue_high (ESTIMATED gross annual revenue EUR = nights x price))
fact_review_month(listing_id FK, month_start DATE, n_reviews INT)           -- reviews per listing per month (demand proxy), 2015-2026; 2026-09 is partial
fact_availability_week(week_start DATE, neighbourhood_key FK, room_type, listing_days INT, unavailable_days INT)   -- forward calendar 2026-09-19..2027-09-19; unavailable = booked OR blocked; no prices
fact_price_gap(listing_id FK, price_eur, pred_price_model, pred_price_baseline, gap_eur, gap_pct, pricing_position)  -- asking price vs model prediction (out-of-fold)
dim_date(date_key INT PK, date DATE, year, quarter, month, month_name, month_start DATE, week_start DATE, iso_day_of_week, is_weekend, season, is_summer, is_christmas_window, event_name, event_is_indicative)

Rules:
- Join facts to dimensions on the *_key / listing_id columns. District names live in dim_neighbourhood.district.
- BENCHMARK POPULATION: unless the question asks about all/inactive/mid-term listings, filter dim_listing.is_benchmark = TRUE for price, revenue and occupancy questions (priced, short-stay, price 10-1000 EUR).
- Use MEDIAN(x) for 'typical' price/revenue (prices are skewed). All occupancy/revenue columns are estimates.
- There is NO calendar price and NO host name/id in the data. If a question cannot be answered from these tables, answer with exactly: SELECT 'cannot be answered from the available data' AS message
- Output ONE DuckDB SELECT statement only (CTEs allowed). No comments, no explanations. Add ORDER BY and LIMIT where sensible (max 200 rows).
""".strip()

FEW_SHOT = [
    ("How many listings are there in each room type?",
     "SELECT room_type, COUNT(*) AS listings FROM dim_listing GROUP BY room_type ORDER BY listings DESC"),
    ("Which three districts have the highest median price for private rooms?",
     "SELECT n.district, MEDIAN(f.price_eur) AS median_price FROM fact_listing f JOIN dim_listing d USING (listing_id) "
     "JOIN dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key WHERE d.is_benchmark AND d.room_type = 'Private room' "
     "GROUP BY n.district ORDER BY median_price DESC LIMIT 3"),
    ("Total reviews per year since 2022",
     "SELECT year(month_start) AS year, SUM(n_reviews) AS reviews FROM fact_review_month WHERE year(month_start) >= 2022 GROUP BY 1 ORDER BY 1"),
]
