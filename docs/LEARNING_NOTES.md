# Learning Notes

One entry per major step: what we did, why, the key concept, a short plain explanation, a likely interview question with a good answer, and where it lives.

---
## V1 - Market Analytics

### 1. Profile the data before designing anything
- **What/why:** Before writing models we queried the raw files (row counts, types, null rates, sample values). This found that the calendar has no price column, host fields are empty, price is text like `$97.00`, and 34% of listings have no price.
- **Concept:** data profiling / schema-on-read. Designs built on assumptions break; designs built on profiles do not.
- **Plain explanation:** Reading a file's real shape first costs minutes and prevents building the wrong thing (here: a price-seasonality analysis that the data cannot support). We changed the plan because of it.
- **Interview Q:** *"Tell me about a time the data didn't match expectations."* **A:** "The calendar I expected to give seasonal prices had no price column. I switched to review dates as a demand proxy, stated that price seasonality could not be measured, and documented the limit instead of faking it."
- **Where:** `docs/BUILD_PLAN.md`, `docs/DATA_QUALITY_REPORT.md`.

### 2. Layered warehouse: raw -> staging -> marts -> analysis
- **What/why:** `src/load_data.py` loads untouched files into `raw`; `sql/01_staging.sql` types and cleans; `sql/02-03` build the star schema; `sql/1x` answer questions.
- **Concept:** ELT layering. Raw stays reproducible and auditable; cleaning rules live in one place; business logic sits downstream.
- **Plain explanation:** If a number looks wrong you can trace it back layer by layer. Changing a cleaning rule means editing one file and rebuilding, not hunting through queries.
- **Interview Q:** *"Why not clean in the load step?"* **A:** "Because then you cannot audit or change a rule without reloading and you lose the original. ELT keeps raw immutable and makes transformations reviewable SQL."
- **Where:** `src/load_data.py`, `sql/00-03*.sql`, `src/run_sql.py`.

### 3. Flag, don't delete (outliers and the benchmark population)
- **What/why:** Prices outside 10-1,000 EUR get `is_price_outlier` and a NULL `price_eur`; mid-term (28+ nights) and unpriced listings are separate segments; `is_benchmark` defines the population for statistics.
- **Concept:** explicit population definition; outlier handling that is transparent and reversible; medians are robust to skew.
- **Plain explanation:** A 10,000 EUR/night listing or a 90-night minimum stay is not "wrong", it is a different market. We keep it but keep it out of the tourist-price benchmark, and say so.
- **Interview Q:** *"How did you handle outliers?"* **A:** "A simple documented rule (10-1,000 EUR) that removed 27 listings from price stats, kept the rows with a flag, compared it with an IQR rule, and used medians so the result barely depends on the cut."
- **Where:** `sql/01_staging.sql`, notebook section 2.

### 4. Star schema and grain
- **What/why:** `fact_listing` (one row per listing), `fact_listing_day` (listing x day), `fact_review_month` (listing x month), plus `dim_listing`, `dim_neighbourhood`, `dim_date`, `dim_host_type`. Grain and keys are written down in `docs/DATA_MODEL.md`.
- **Concept:** dimensional modelling; **grain** = what one row means; surrogate vs natural keys.
- **Plain explanation:** Facts hold numbers, dimensions hold the labels you slice by. Stating the grain first prevents double counting (e.g. summing a listing-level price across daily rows).
- **Interview Q:** *"What is the grain of your fact table and why does it matter?"* **A:** "One row per listing for snapshot metrics, and a separate daily fact for the calendar. Mixing grains in one table would inflate sums; separate facts keep every aggregation correct."
- **Where:** `sql/02_dimensions.sql`, `sql/03_facts.sql`, `docs/DATA_MODEL.md`.

### 5. Data quality as a deliverable (the review_id finding)
- **What/why:** The DQ report found `review_id` is not unique (3,676 ids under 2+ listings, ~6.6k extra rows, mostly 2026, 43 hosts). We de-duplicate on `review_id`; this changed 2026 YoY growth from 18.4% to 15.4%.
- **Concept:** uniqueness / orphan checks, quantifying the impact of a cleaning decision.
- **Plain explanation:** A silent duplicate would have overstated growth by three points. Always measure what a fix changes and write it down.
- **Interview Q:** *"How do you validate data?"* **A:** "Row counts against source, key uniqueness, orphan keys, null rates, ranges, then business-logic reconciliation. Each check is a query in a report that regenerates on every run, and the key ones are automated tests."
- **Where:** `src/dq_report.py`, `docs/DATA_QUALITY_REPORT.md`, `tests/test_pipeline.py`.

### 6. Window functions and CTEs
- **What/why:** `RANK()` for district price ranking, `LAG()` for year-on-year and week-on-week change, `AVG() OVER (ROWS BETWEEN ...)` for 3- and 12-month rolling averages, `SUM() OVER` for cumulative shares and shares of total.
- **Concept:** window = a calculation over related rows without collapsing them (unlike GROUP BY).
- **Plain explanation:** `LAG(x, 12)` looks 12 rows back (one year of monthly data); a rolling average smooths noise. CTEs name each step so a long query reads top to bottom.
- **Interview Q:** *"GROUP BY vs window function?"* **A:** "GROUP BY returns one row per group; a window function keeps every row and adds a calculation over a partition, e.g. each district's rank next to its own row."
- **Where:** `sql/10`, `11`, `14a`, `15a`, `16`.

### 7. Estimating occupancy honestly
- **What/why:** Real bookings are not public. We estimate nights = reviews_ltm / review_rate x max(min_nights, avg_stay), capped at 255, then revenue = nights x price. By testing parameter sets we found `review_rate 0.5, avg_stay 6.3` reproduces Inside Airbnb's own column for 98.4% of listings, and built low/high scenarios around it.
- **Concept:** proxy modelling, reconciliation against a reference, scenario/sensitivity ranges instead of one false-precise number.
- **Plain explanation:** A review is evidence of a stay, not a count of stays. So we publish a range and list the biases (zero-review listings get zero nights; today's price applied backwards).
- **Interview Q:** *"How reliable is your revenue estimate?"* **A:** "It is an estimate: it reproduces a published reference but both rest on assumed review and stay rates. I show low/base/high (roughly -35% / +11% around the base median), state the biases, and say it is gross income, not profit."
- **Where:** `sql/00_assumptions.sql`, `sql/03_facts.sql`, `docs/DATA_MODEL.md`.

### 8. Seasonality with a confound
- **What/why:** Review dates give a monthly seasonal index; the forward calendar gives booking pressure by week and event. But near-term nights are fuller than far-future nights, so lead time is mixed into the forward curve. We compare event days with other days of the same months and label this directional.
- **Concept:** confounding; proxy variables; not claiming more than the data supports.
- **Plain explanation:** If September looks "busy" in a calendar scraped in September, part of that is simply that it is close. Comparing like with like reduces the bias but does not remove it.
- **Interview Q:** *"What are the limits of your seasonality analysis?"* **A:** "Reviews lag stays, the forward calendar confounds lead time with season and cannot separate booked from blocked nights, and there are no calendar prices, so I can describe demand timing but not price premiums."
- **Where:** `sql/14b`, `sql/15a`, `sql/15b`, notebook sections 5-6.

### 9. Privacy by design
- **What/why:** The `license` text can contain private persons' names, so only a category is kept; names, descriptions, URLs and review comments are never loaded into model tables; host ids are hashed and excluded from exports; a test scans exports for banned columns.
- **Concept:** data minimisation (GDPR principle), aggregate-only reporting.
- **Plain explanation:** The safest personal data is data you never copied. Public data is not automatically fine to republish at individual level.
- **Interview Q:** *"How did you handle personal data in a public dataset?"* **A:** "Minimised it at the staging layer, hashed identifiers, reported aggregates only, and added an automated test so a future change cannot leak a column."
- **Where:** `sql/01_staging.sql`, `src/export.py`, `tests/test_pipeline.py::test_no_sensitive_columns_in_exports`.

### 10. Testing a data model
- **What/why:** 20 pytest checks: unique keys, composite grains, foreign keys, row counts, price parsing, occupancy cap/order and reconciliation, no sensitive columns.
- **Concept:** data tests = executable assumptions; the same idea as dbt tests (V2).
- **Plain explanation:** If a rebuild breaks a join or duplicates rows, a test fails instead of a wrong chart reaching a reader.
- **Interview Q:** *"How do you know the pipeline is correct?"* **A:** "Automated tests on keys, referential integrity and reconciliation to an external reference, run after every full rebuild."
- **Where:** `tests/test_pipeline.py`.

### 11. Power BI: star model and DAX
- **What/why:** `docs/POWERBI_GUIDE.md` specifies relationships (dimension -> fact, single direction), measures (`CALCULATE` with a benchmark filter, `MEDIAN`, `SAMEPERIODLASTYEAR`, `DATESINPERIOD`, `DIVIDE`) and a reconciliation checklist against the SQL numbers.
- **Concept:** filter context; measures vs calculated columns; a star schema keeps DAX simple.
- **Plain explanation:** A measure is recalculated for whatever the user slices; `CALCULATE` changes that context (here: always benchmark listings).
- **Interview Q:** *"Measure or calculated column?"* **A:** "A calculated column is computed per row at refresh and stored; a measure is computed at query time in the current filter context. Ratios and medians must be measures."
- **Where:** `docs/POWERBI_GUIDE.md`, `powerbi/`.

### 12. EDA discipline: median, segments, correlation caveats
- **What/why:** Notebook defines the population, uses medians, shows Spearman correlations, a map with small-sample masking, and a concentration curve.
- **Concept:** skewed distributions, rank correlation, small-n suppression, correlation is not causation.
- **Plain explanation:** The mean (182 EUR) is pulled up by luxury listings; the median (150 EUR) is what a typical listing charges. Districts with under 20 listings are greyed out rather than coloured misleadingly.
- **Interview Q:** *"Why Spearman instead of Pearson?"* **A:** "Prices are skewed with outliers and relationships are monotonic rather than linear; rank correlation is robust to both."
- **Where:** `notebooks/01_eda.ipynb`.
