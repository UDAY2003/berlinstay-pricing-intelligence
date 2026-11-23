# Power BI Build Guide (V1)

You build the dashboard yourself in Power BI Desktop (Windows). Everything you need is in `powerbi/` (small CSVs, UTF-8 with BOM, plus `neighbourhoods.geojson`).
Data credit (put it on the last page footer): **Data: Inside Airbnb (insideairbnb.com), CC BY 4.0, scrape 19 Sep 2026.**
All occupancy/revenue numbers are **estimates**; say so on the relevant visuals.

## 1. Load the data
Home > Get data > Text/CSV, for each file (File origin: **65001 UTF-8**): `dim_listing`, `dim_neighbourhood`, `dim_host_type`, `dim_date`, `fact_listing`, `fact_review_month`, `fact_availability_week`, `analysis_seasonal_index`, `analysis_monthly_review_series`, `analysis_forward_availability_weekly`, `analysis_forward_availability_events`, `analysis_review_demand_trends`, `analysis_neighbourhood_summary`.
In Power Query set types: all `*_key` and `listing_id` = Whole number; `date`, `month_start`, `week_start`, `first_day_in_data`, `start_date`, `end_date` = Date; `is_*`, `has_*` columns = True/False; prices/revenues = Decimal number.
Rename tables exactly as the files (without `analysis_` prefix is fine, just stay consistent with the measures below).

## 2. Data model (Model view)
Star schema, **single-direction** filters from dimensions to facts:

| From (one side) | To (many side) | Cardinality |
|---|---|---|
| `dim_neighbourhood[neighbourhood_key]` | `fact_listing[neighbourhood_key]` | 1:* |
| `dim_neighbourhood[neighbourhood_key]` | `fact_availability_week[neighbourhood_key]` | 1:* |
| `dim_host_type[host_type_key]` | `fact_listing[host_type_key]` | 1:* |
| `dim_listing[listing_id]` | `fact_listing[listing_id]` | 1:1 (set filter direction **Both**; this lets listing-level slicers such as room type, capacity band and license status filter the fact) |
| `dim_listing[listing_id]` | `fact_review_month[listing_id]` | 1:* |
| `dim_date[date]` | `fact_review_month[month_start]` | 1:* |
| `dim_date[date]` | `fact_availability_week[week_start]` | 1:* (make this one **inactive** if Power BI warns about ambiguity, and use USERELATIONSHIP in the measure) |

Disconnected tables (no relationships): the `analysis_*` tables; they are pre-computed and plotted as-is.
Mark `dim_date` as a Date table (Table tools > Mark as date table > `date`). Hide `*_key` columns in Report view.
Add a calculated column `dim_neighbourhood[district_short] = dim_neighbourhood[district]` only if you want shorter labels.

## 3. DAX measures (create a `_Measures` table: Home > Enter data, name it `_Measures`, then add)
```DAX
Benchmark Listings =
CALCULATE ( COUNTROWS ( fact_listing ), dim_listing[is_benchmark] = TRUE () )

All Listings = COUNTROWS ( fact_listing )

Benchmark Share % = DIVIDE ( [Benchmark Listings], [All Listings] )

Median Price =
CALCULATE ( MEDIAN ( fact_listing[price_eur] ), dim_listing[is_benchmark] = TRUE () )

Price P25 =
CALCULATE ( PERCENTILE.INC ( fact_listing[price_eur], 0.25 ), dim_listing[is_benchmark] = TRUE () )

Price P75 =
CALCULATE ( PERCENTILE.INC ( fact_listing[price_eur], 0.75 ), dim_listing[is_benchmark] = TRUE () )

Median Est. Revenue (Base) =
CALCULATE ( MEDIAN ( fact_listing[est_revenue_base] ), dim_listing[is_benchmark] = TRUE () )

Median Est. Revenue (Low) =
CALCULATE ( MEDIAN ( fact_listing[est_revenue_low] ), dim_listing[is_benchmark] = TRUE () )

Median Est. Revenue (High) =
CALCULATE ( MEDIAN ( fact_listing[est_revenue_high] ), dim_listing[is_benchmark] = TRUE () )

Median Est. Nights =
CALCULATE ( MEDIAN ( fact_listing[est_nights_base] ), dim_listing[is_benchmark] = TRUE () )

Avg Est. Occupancy % =
CALCULATE ( AVERAGE ( fact_listing[est_occupancy_rate_base] ),
            dim_listing[is_benchmark] = TRUE (), fact_listing[number_of_reviews_ltm] > 0 )

Zero-Review Share % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_listing ), dim_listing[is_benchmark] = TRUE (), fact_listing[number_of_reviews_ltm] = 0 ),
    [Benchmark Listings]
)

Price Index vs City =
VAR cityMedian = CALCULATE ( [Median Price], ALL ( dim_neighbourhood ) )
RETURN DIVIDE ( [Median Price], cityMedian )

Total Est. Revenue (EUR m) =
DIVIDE ( CALCULATE ( SUM ( fact_listing[est_revenue_base] ), dim_listing[is_benchmark] = TRUE () ), 1000000 )

Revenue Share % =
DIVIDE ( [Total Est. Revenue (EUR m)],
         CALCULATE ( [Total Est. Revenue (EUR m)], ALL ( dim_host_type ), ALL ( dim_neighbourhood ) ) )

Listings Share % =
DIVIDE ( [Benchmark Listings], CALCULATE ( [Benchmark Listings], ALL ( dim_host_type ) ) )

Reviews = SUM ( fact_review_month[n_reviews] )

Reviews Prior Year =
CALCULATE ( [Reviews], SAMEPERIODLASTYEAR ( dim_date[date] ) )

Reviews YoY % = DIVIDE ( [Reviews] - [Reviews Prior Year], [Reviews Prior Year] )

Reviews Rolling 12M =
CALCULATE ( [Reviews], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ) )

Unavailable % (forward) =
DIVIDE ( SUM ( fact_availability_week[unavailable_days] ), SUM ( fact_availability_week[listing_days] ) )

Registration-Number Share % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_listing ), dim_listing[is_benchmark] = TRUE (), dim_listing[license_status] = "registration_number" ),
    [Benchmark Listings]
)
```
`Reviews Prior Year`/`Rolling 12M` need the month axis from `dim_date` (use `dim_date[month_start]` or Year-Month hierarchy). Filter the report to 2015 onward and exclude the partial month Sep 2026 (visual filter: `dim_date[date] < 1 Sep 2026`).

**Reconciliation check (your DAX must match the SQL, otherwise something is wrong):** `Benchmark Listings` = **6,456**; `All Listings` = **12,376**; `Median Price` (no slicers) = **150.2**; entire-home median = **181**; private-room median = **91**; Mitte entire-home median = **205**.

## 4. Pages, visuals and slicers
Theme: one accent colour (e.g. #2a6f97) plus grey; orange only for highlights. Title on every page; subtitle with population ("Benchmark listings: priced, short-stay, 10-1,000 EUR").

**Page 1 - Market Overview**
- Cards: `Benchmark Listings`, `Benchmark Share %`, `Median Price`, `Median Est. Revenue (Base)`.
- Filled map or shape map: load `neighbourhoods.geojson` (Format > Shape map > Add map > Custom). Location = `analysis_neighbourhood_summary[neighbourhood]`, colour saturation = median price. (If the shape map does not match the German characters, use Azure Map with `latitude/longitude` from `dim_listing`, bubble size = count, colour = `Median Price`.)
- Clustered bar: `dim_neighbourhood[district]` x `Benchmark Listings`, sorted descending.
- Donut: `dim_listing[listing_segment]` over all listings (shows the 52% / 34% / 13% split; uses a count of `fact_listing` with no benchmark filter, so use a plain `COUNTROWS`).
- Slicers (sync across pages): `dim_listing[room_type]`, `dim_neighbourhood[district]`, `dim_listing[capacity_band]`.

**Page 2 - Price Explorer**
- Matrix: rows = `district`, columns = `room_type`, values = `Median Price`; conditional formatting (background colour scale).
- Box-like visual: clustered column of `Price P25`, `Median Price`, `Price P75` by `district`.
- Bar: `Median Price` by `dim_listing[capacity_band]` (entire homes only via slicer).
- Table: `neighbourhood`, `n_listings`, `median_price` from `analysis_neighbourhood_summary` with filter `is_reliable_sample = TRUE`, top N by price.
- Tooltip page: `Benchmark Listings`, `Price Index vs City`.

**Page 3 - Occupancy and Revenue (ESTIMATES)**
- Clustered column: `Median Est. Revenue (Low)`, `(Base)`, `(High)` by `room_type`; title "Estimated annual revenue range".
- Scatter: x = `Median Price`, y = `Median Est. Nights`, size = `Benchmark Listings`, detail = `district`.
- Cards: `Avg Est. Occupancy %`, `Zero-Review Share %`.
- Info box (text): the formula from `docs/DATA_MODEL.md` and the limits.

**Page 4 - Seasonality and Events**
- Column chart: `analysis_seasonal_index[month_name]` (sort by `month`) x `seasonal_index`; constant line at 1.0.
- Line chart: `dim_date[month_start]` x `Reviews` and `Reviews Rolling 12M`.
- Line chart: `analysis_forward_availability_weekly[week_start]` x `unavailable_pct` (filter `listing_days` > 20000 to drop the partial first week); event labels as data labels on `event_name`.
- Table: `analysis_forward_availability_events` (event, `uplift_pp`, `window_is_indicative`).
- Text note: "Forward calendar mixes seasonality with booking lead time; unavailable = booked or blocked. Event dates marked indicative must be verified."

**Page 5 - Supply and Hosts**
- Clustered bar: `dim_host_type[host_type]` x `Listings Share %` and `Revenue Share %`.
- 100% stacked column: `host_type` x `room_type` counts.
- Line/bar: `analysis_review_demand_trends` (filter `year_ytd_aug = 2026`) district x `yoy_pct`.
- Card/table: `Registration-Number Share %` by `host_type` (label: "licence field entry looks like a registration number; descriptive, not a compliance check").

**Page 6 - About and data notes**: source and licence, scrape date, definitions, estimate disclaimers, known limits (copy from `docs/DATA_MODEL.md`), link to the repo.

## 5. Quality checklist
- Reconcile the six numbers in section 3. Every page has a population subtitle. Estimates are labelled "estimate". No host names or identifiers anywhere (none exist in the files).
- Interactions: slicers sync on room type and district; Edit interactions so slicers do not filter the pre-computed `analysis_*` visuals.
- Export a PDF and 2-3 screenshots into `docs/img/` for the README.
