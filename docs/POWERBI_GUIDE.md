# Power BI Build Guide (V1)

You build the dashboard yourself in Power BI Desktop (Windows). Everything you need is in `powerbi/` (small CSVs, UTF-8 with BOM, plus `neighbourhoods.geojson`).
Data credit (put it on the last page footer): **Data: Inside Airbnb (insideairbnb.com), CC BY 4.0, scrape 19 Sep 2026.**
All occupancy/revenue numbers are **estimates**; say so on the relevant visuals.

## 1. Load the data
> **Berlin/German locale warning (most likely source of wrong numbers):** the CSVs use a **dot** as the decimal separator and ISO dates (`2026-09-19`). Power BI reads CSV text with your computer's regional settings, and on a German locale a value such as `150.16` can be read as 15016 or fail. Avoid this once, before loading anything: **File > Options and settings > Options > Current File > Regional Settings > Locale for import = English (United States)**. If you change column types in Power Query later, use *Change Type > Using Locale... > English (United States)* for decimals and dates. Check after loading: `price_eur` must show values like 97 or 150.16, never 15016.

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

**Full reference:** every measure below, with expected values for two slicer settings, is in `docs/POWERBI_EXPECTED_VALUES.md` (put each measure in a Card, apply the slicers, compare). `Reviews Rolling 12M` is a **sum** of the last 12 months (the SQL series `rolling_12m` is an average).

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
- Text note: "Forward calendar mixes seasonality with booking lead time; unavailable = booked or blocked. Event dates were checked against official sources on 23 Nov 2026; re-check before relying on them."

**Page 5 - Supply and Hosts**
- Clustered bar: `dim_host_type[host_type]` x `Listings Share %` and `Revenue Share %`.
- 100% stacked column: `host_type` x `room_type` counts.
- Line/bar: `analysis_review_demand_trends` (filter `year_ytd_aug = 2026`) district x `yoy_pct`.
- Card/table: `Registration-Number Share %` by `host_type` (label: "licence field entry looks like a registration number; descriptive, not a compliance check").

**Page 6 - About and data notes**: source and licence, scrape date, definitions, estimate disclaimers, known limits (copy from `docs/DATA_MODEL.md`), link to the repo.

## 5. Quality checklist
- Locale for import is English (United States) (see section 1) and `price_eur` shows 97 / 150.16, not 15016.
- Mark `dim_date` as a Date table and confirm `dim_date` has no gaps (it is a contiguous daily table 2015-2027); `SAMEPERIODLASTYEAR` and `DATESINPERIOD` depend on that.
- Every measure card matches `docs/POWERBI_EXPECTED_VALUES.md` for scenario A (no slicers) and scenario B (Entire home + Mitte).
- Reconcile the six numbers in section 3. Every page has a population subtitle. Estimates are labelled "estimate". No host names or identifiers anywhere (none exist in the files).
- Interactions: slicers sync on room type and district; Edit interactions so slicers do not filter the pre-computed `analysis_*` visuals.
- Export a PDF and 2-3 screenshots into `docs/img/` for the README.

---
# V2 additions: Pricing gaps and Scenarios (pages 7 and 8)

New files in `powerbi/` (re-run `python -m src.run_v2` to refresh): `fact_price_gap.csv`, `scenario_cap_sensitivity.csv`, `scenario_cap_by_district_base_20pct.csv`.

## Model additions
| From | To | Cardinality |
|---|---|---|
| `dim_listing[listing_id]` | `fact_price_gap[listing_id]` | 1:1 (direction Both, same as `fact_listing`) |

`scenario_cap_*` tables are **disconnected** (pre-computed). Set types: `share_second_homes` as Percentage; `lost_revenue`, `net_lost_revenue` Decimal; `occupancy_scenario` and `displacement` as Text (set `displacement` to Text so it works as a slicer: 0.0 / 0.5).

## Extra DAX measures
```DAX
Median Predicted Price =
CALCULATE ( MEDIAN ( fact_price_gap[pred_price_model] ), dim_listing[is_benchmark] = TRUE () )

Median Gap EUR = MEDIAN ( fact_price_gap[gap_eur] )

Median Gap % = MEDIAN ( fact_price_gap[gap_pct] )

Share Priced Above Model % =
DIVIDE ( CALCULATE ( COUNTROWS ( fact_price_gap ), fact_price_gap[pricing_position] = "above model (>20% over)" ),
         COUNTROWS ( fact_price_gap ) )

Share Priced Below Model % =
DIVIDE ( CALCULATE ( COUNTROWS ( fact_price_gap ), fact_price_gap[pricing_position] = "below model (>20% under)" ),
         COUNTROWS ( fact_price_gap ) )

Model MAE EUR = AVERAGEX ( fact_price_gap, ABS ( fact_price_gap[gap_eur] ) )

Baseline MAE EUR = AVERAGEX ( fact_price_gap, ABS ( fact_price_gap[price_eur] - fact_price_gap[pred_price_baseline] ) )

Scenario Lost Revenue EUR m =
DIVIDE ( SUM ( scenario_cap_sensitivity[net_lost_revenue] ), 1000000 )
```
Reconciliation: `Share Priced Above Model %` = **27.8%**, `Below` = **27.7%**, in line = **44.5%**; `Model MAE EUR` should be close to **54-56** (out-of-fold over all 6,456 listings) and `Baseline MAE EUR` clearly higher.

## Page 7 - Pricing gaps (model vs asking price)
- Cards: `Median Gap %`, `Share Priced Above Model %`, `Share Priced Below Model %`, `Model MAE EUR`, `Baseline MAE EUR`.
- Scatter: x = `fact_price_gap[pred_price_model]`, y = `fact_price_gap[price_eur]`, detail = `listing_id`, add a constant/diagonal reference line (Analytics pane: y = x via an X=Y line, or a second series). Colour by `pricing_position`. Cap axes at 600 EUR.
- Clustered bar: `dim_neighbourhood[district]` x `Median Gap %`.
- Column: `dim_listing[capacity_band]` x `Share Priced Above Model %` and `Share Priced Below Model %`.
- Slicers: `room_type`, `district`, `pricing_position`.
- Mandatory note on the page: "Gap = asking price minus what the model predicts for comparable listings (predictions are out-of-fold, the model never saw the listing's host). A gap is not an error: the model does not see photos, quality or exact micro-location. Use it to shortlist listings to review, not to conclude a price is wrong."

## Page 8 - Scenarios (90-night cap, labelled SCENARIO)
- Banner (text box, top): "Scenario, not legal advice and not a forecast. Which listings are second homes is unknown; the share is an assumption. Verify rules on official Berlin sources."
- Slicers on `scenario_cap_sensitivity`: `occupancy_scenario` (low/base/high), `displacement` (0.0 / 0.5).
- Line chart: x = `share_second_homes`, y = `pct_of_market_revenue` (Sum), legend = `occupancy_scenario`.
- Card: `Scenario Lost Revenue EUR m` (slice at share = 20%, base, displacement 0.0 expected ~4.3).
- Table: `scenario_cap_by_district_base_20pct` columns `district`, `pool_listings`, `pool_over_cap_pct`, `lost_revenue` (format as EUR m).
- Footnote: assumptions from `docs/REGULATION_SCENARIO.md`.
