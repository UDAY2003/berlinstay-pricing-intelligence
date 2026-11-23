# Data Quality Report

Scrape: Inside Airbnb Berlin, 2026-09-19. Generated 2026-11-23 by `src/dq_report.py` from the DuckDB `raw` schema. Re-run `python -m src.run_pipeline` to refresh.

## 1. Row counts

| tbl | rows |
|---|---|
| raw.listings | 12,376 |
| raw.calendar | 4,517,243 |
| raw.reviews | 708,768 |
| raw.neighbourhoods | 139 |


## 2. Keys, duplicates and orphans

| check | n_bad |
|---|---|
| neighbourhoods.csv: blank rows (dropped) | 1 |
| listings: duplicate ids | 0 |
| reviews: review_id shared by 2+ listings | 3,676 |
| calendar: duplicate (listing, date) | 0 |
| calendar: listing_id not in listings | 0 |
| reviews: listing_id not in listings | 0 |
| listings: neighbourhood not in neighbourhoods.csv | 0 |
| listings: no host-type bucket | 0 |


## 3. Calendar completeness

| first_day | last_day | listings | rows | pct_unavailable |
|---|---|---|---|---|
| 2026-09-19 | 2027-09-19 | 12376 | 4517243 | 55.8 |


Days per listing (top values): 365 days = 12,373 listings, 366 days = 3 listings.

**Finding:** the calendar has **no price column** in this release and covers only the next 365 days, so price seasonality cannot be measured from it.


## 4. Null rates of key listing columns

| column | pct_null |
|---|---|
| price | 34.10 |
| bedrooms | 0.10 |
| beds | 3.10 |
| bathrooms_text | 0.10 |
| review_scores_rating | 18.10 |
| reviews_per_month | 18.10 |
| license | 32.60 |
| host_since | 100.00 |
| host_response_rate | 100.00 |
| host_total_listings_count | 100.00 |
| instant_bookable | 100.00 |
| estimated_revenue_l365d | 34.10 |


**Findings:** host_since, host_response_rate, host_total_listings_count and instant_bookable are 100% empty in this scrape, so host type is derived from `calculated_host_listings_count`. Missing price (see section 5) marks listings that are not currently bookable.


## 5. Price parsing and outliers

| listings | price_text_present | parsed_ok | parse_failed | no_price |
|---|---|---|---|---|
| 12,376 | 8,157 | 8,157 | 0 | 4,219 |


| min | p01 | median | p99 | max | below_10 | above_1000 |
|---|---|---|---|---|---|---|
| 12.90 | 26.30 | 129.50 | 691.20 | 10,025.00 | 0 | 27 |


**Rule:** prices outside 10-1,000 EUR/night are flagged `is_price_outlier` and excluded from price statistics (kept in the data, never deleted). Currency: the `$` in the source text is formatting; the price quote metadata says EUR.


## 6. Listing segments (what counts as 'the market')

| listing_segment | listings | pct |
|---|---|---|
| Short-stay | 6,481 | 52.40 |
| No price (inactive/unbookable) | 4,219 | 34.10 |
| Mid-term (28+ nights) | 1,676 | 13.50 |


**Benchmark population** (`is_benchmark`): priced, average minimum stay under 28 nights, price 10-1,000 EUR = **6,456 listings**. All price and revenue statistics use it unless stated.


## 7. Reviews date range

| first_review | last_review | reviews |
|---|---|---|
| 2009-06-20 | 2026-09-20 | 708768 |


2026 is a partial year (ends 20 Sep). Reviews of listings that have left the platform are absent (survivorship): early years are understated.


## 8. Occupancy-formula reconciliation

| listings | pct_within_1_night_of_inside_airbnb | pct_revenue_within_2_eur |
|---|---|---|
| 12,376 | 98.40 | 97.10 |


Our 'base' scenario (review rate 0.50, average stay 6.3 nights, cap 255 nights) was reverse-engineered from the `estimated_occupancy_l365d` column and matches it for the share above. It is an **estimate**, not a measurement. Low/high scenarios are our own sensitivity bounds.


## 9. Sensitive fields

| license_status | listings |
|---|---|
| registration_number | 4,287 |
| missing | 4,040 |
| legal_entity_stated | 2,351 |
| person_stated | 1,591 |
| exempt | 75 |
| other_format | 32 |


The raw `license` text can contain private persons' names, so only the category above is carried into the model. Names, descriptions, host names/about, URLs, pictures and review comments are not loaded into any model table. `host_key` is an MD5 hash used only for counting and is excluded from every export.
