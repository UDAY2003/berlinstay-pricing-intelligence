# Data Model (V1)

Layers in `data/berlinstay.duckdb`: **raw** (untouched source) -> **stg** (typed, cleaned, flags) -> **mart** (star schema) -> **analysis** (SQL answers) -> **ref** (assumptions).
Built by `sql/00..03*.sql`; analysis by `sql/1x_*.sql`; run with `python -m src.run_pipeline`.

## Star schema

```
                       dim_date (date_key)
                          |  month_start / week_start
 dim_neighbourhood --- fact_listing --- dim_host_type
   (neighbourhood_key)    |  listing_id     (host_type_key)
                          |
                      dim_listing  --- fact_review_month   (listing_id, month_start)
                          |         --- fact_listing_day     (listing_id, date_key)  [DuckDB only: 4.5M rows]
                          +---------- fact_availability_week (week, neighbourhood_key, room_type) [aggregate for Power BI]
```

| Table | Grain (one row per...) | Key | Notes |
|---|---|---|---|
| `dim_listing` | listing (snapshot 2026-09-19) | `listing_id` | descriptive attributes, flags, `listing_segment`; hashed `host_key` (never exported) |
| `dim_neighbourhood` | Ortsteil (138) | `neighbourhood_key` | `district` = Bezirk (12) |
| `dim_host_type` | host-size bucket (4) | `host_type_key` | from `calculated_host_listings_count` (host_since etc. are empty in this scrape) |
| `dim_date` | calendar day 2009-2027 | `date_key` (yyyymmdd) | season, weekend, Christmas window, event name (`event_is_indicative`) |
| `fact_listing` | listing | `listing_id` (+ FK `neighbourhood_key`, `host_type_key`) | price, availability, reviews, estimated nights/revenue low-base-high |
| `fact_listing_day` | listing x future day (4,517,243) | (`listing_id`, `date_key`) | `is_available` FALSE = booked OR host-blocked |
| `fact_review_month` | listing x month with >=1 review | (`listing_id`, `month_start`) | de-duplicated reviews; demand proxy |
| `fact_availability_week` | week x neighbourhood x room type | (`week_start`, `neighbourhood_key`, `room_type`) | benchmark listings only |

## Definitions and rules
- **Active listing** = has a price. **Mid-term** = average minimum stay >= 28 nights. **Benchmark population** (`is_benchmark`) = priced AND not mid-term AND price in 10-1,000 EUR (6,456 listings). All price/revenue statistics use it unless stated.
- **Price**: source text such as `$97.00` parsed to a number (currency is EUR). Values outside 10-1,000 are flagged `is_price_outlier` and set to NULL in `price_eur` (raw value kept in `price_raw`).
- **Reviews** are de-duplicated on `review_id` (see DATA_QUALITY_REPORT section 2).
- **License field** is reduced to `license_status` (registration_number / exempt / legal_entity_stated / person_stated / other_format / missing). It is descriptive, not a compliance check.

## Occupancy and revenue formula (ESTIMATES)
```
est_nights   = LEAST(255, ROUND( reviews_ltm / review_rate * GREATEST(min_nights_avg, avg_stay) ))
est_revenue  = est_nights * price_eur            (gross, today's price applied to the past 12 months)
est_occupancy_rate = est_nights / 365
```
| Scenario | review_rate | avg_stay (nights) | Meaning |
|---|---|---|---|
| low  | 0.60 | 4.0 | fewer nights per review |
| **base** | **0.50** | **6.3** | reproduces Inside Airbnb's `estimated_occupancy_l365d` for 98.4% of listings (within 1 night) |
| high | 0.40 | 6.3 | more nights per review |

Cap 255 nights = 70% of the year. Parameters live in `ref.occupancy_assumptions` (`sql/00_assumptions.sql`). **They are assumptions, not measurements.**
Known biases: listings with 0 reviews in the last 12 months get 0 nights (understates quiet-but-booked listings); today's price is applied retroactively; host fees, cleaning fees, taxes and costs are ignored; the review rate probably differs by listing type.

## Event windows
`ref.event_window` (SQL) / `seeds/event_window.csv` (dbt). Dates checked on 2026-11-23 against: berlin marathon race day 27 Sep 2026 (official race results/organiser pages, window = race weekend 26-27 Sep), Festival of Lights 9-18 Oct 2026 (festival-of-lights.de), Berlinale 10-21 Feb 2027 (berlinale.de), ITB 16-18 Mar 2027 (itb.com; a one-time shift from early March), Berlin Pride/CSD parade 24 Jul 2027 (berlin.de, single day), Easter = Good Friday to Easter Monday 26-29 Mar 2027 (public holidays), Christmas/New Year = 20 Dec - 2 Jan (our definition). Organisers can still change dates; the window boundaries are our definition. `is_indicative` = TRUE would flag an unverified row (none now).

## Known limits
Occupancy is an estimate; the calendar cannot separate booked from blocked nights and has **no price column**; the forward calendar mixes seasonality with booking lead time; locations are anonymised (~150 m); the data is one snapshot; reviews of delisted listings are missing; only aggregates are reported and no host is identified.
