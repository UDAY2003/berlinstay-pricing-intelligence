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

---
## V2 - Pricing and Scenarios

### 13. dbt: models, layers, tests, docs
- **What/why:** V1's plain SQL became a dbt-duckdb project (`dbt_project/`): `staging` views -> `intermediate` tables (flags, occupancy estimates) -> `marts` (star schema) + `analysis`. Assumptions and event windows became **seeds** (CSV files under version control). 71 nodes: models plus tests (unique, not_null, accepted_values, relationships, and singular tests for business rules such as "occupancy never exceeds 255 nights").
- **Concept:** declarative transformations with a dependency graph (`ref()`), tests as code, generated docs (`dbt docs generate`).
- **Plain explanation:** `ref('fact_listing')` tells dbt the build order and lets it draw a lineage graph. A test is a query that must return zero rows; `dbt build` runs models and their tests in dependency order and skips what depends on a failure.
- **Interview Q:** *"Why dbt instead of SQL scripts?"* **A:** "Dependencies are explicit so the order is derived, not hand-maintained; tests and documentation live next to the model; the same project works across environments. My dbt `not_null` test immediately found a bug in my own V1 SQL."
- **Where:** `dbt_project/`, run with `cd dbt_project && dbt build --profiles-dir .`.

### 14. Reconciling a migration (before/after)
- **What/why:** `src/reconcile_v1_dbt.py` compares each of 19 V1 tables with its dbt rebuild using `EXCEPT` in both directions. 18 are identical; `dim_listing.is_benchmark` differs for 1,687 rows (V1 gave NULL for unpriced listings because of three-valued logic, dbt gives FALSE). V1 was left untouched on purpose.
- **Concept:** migration validation, SQL three-valued logic (`NULL AND x`).
- **Plain explanation:** `price BETWEEN 10 AND 1000 AND minstay < 28` is NULL, not FALSE, when price is NULL. `WHERE is_benchmark` hides this, but a dashboard would show blanks.
- **Interview Q:** *"How do you prove a refactor didn't change results?"* **A:** "Compare old and new outputs with set differences in both directions and list every intentional difference with its cause."
- **Where:** `docs/V1_V2_RECONCILIATION.md`, `src/reconcile_v1_dbt.py`.

### 15. Honest model comparison: baseline first, grouped split, bootstrap
- **What/why:** Baseline = district x room-type median (plus a stronger one with capacity). LightGBM tuned by a small random search under **GroupKFold by host**; test touched once; paired bootstrap on the MAE difference. Result: MAE 53.6 vs 66.7 EUR (-13.1, 95% CI -15.8 to -10.5); but it is not better for private rooms or the 150-250 EUR band and the 80% interval covers only 72%.
- **Concept:** baseline, leakage, group-aware splitting (the same host's listings are near-duplicates), cross-validation, MAE vs MAPE, bootstrap confidence intervals, calibration of prediction intervals.
- **Plain explanation:** A model is only good relative to a simple alternative. If one host's 20 identical flats land in both train and test, the model "remembers" them and looks better than it is, so we split by host. We report where the model fails, not just where it wins.
- **Interview Q:** *"How do you know your model beats the baseline?"* **A:** "Same host-grouped folds for both, held-out test used once, a paired bootstrap of the error difference, and a segment breakdown showing where the gain disappears."
- **Where:** `src/price_model.py`, `docs/PRICE_MODEL_REPORT.md`.

### 16. Feature choice and leakage by design
- **What/why:** The main model uses only what a host knows before listing (size, type, location, amenities, host size). Review scores/counts are an ablation: they would improve MAE by about 3 EUR, but a new listing has none and they partly encode demand.
- **Concept:** target leakage vs availability at prediction time; ablation study.
- **Plain explanation:** Ask "would I have this value at the moment I need the prediction?" If not, the feature does not belong in the deployable model.
- **Interview Q:** *"What is data leakage? An example from your project?"* **A:** "Information from the future or from the outcome leaking into training. Reviews are an outcome of past pricing and demand, so I excluded them from the main model and kept them only as a labelled comparison."
- **Where:** `src/features.py`, `tests/test_v2.py::test_features_exclude_outcome_columns`.

### 17. Explainability: SHAP
- **What/why:** TreeSHAP on the test set: room type, bedrooms, neighbourhood and capacity drive predictions; the plot is in the report.
- **Concept:** SHAP = each feature's additive contribution to a prediction (here on log price), averaged for global importance.
- **Plain explanation:** Because the model predicts log price, a SHAP value of 0.1 means about +10% for that feature in that listing. Importance is not causation.
- **Interview Q:** *"Why SHAP over built-in feature importance?"* **A:** "It is consistent, signed and local, so I can explain a single prediction, whereas split-count importance is biased toward high-cardinality features."
- **Where:** `docs/PRICE_MODEL_REPORT.md`, `reports/price_model_shap_importance.csv`.

### 18. What-if calculator: association is not elasticity
- **What/why:** `RevenueCalculator` uses comparable listings (with fallbacks when fewer than 30), the listing's price position, and reports p25/median/p75 of estimated nights, plus the occupancy-model uncertainty separately. It warns when estimates hit the 255-night ceiling or extrapolate.
- **Concept:** comparable-set estimation, uncertainty decomposition (between listings vs model assumptions), refusing to over-claim causality.
- **Plain explanation:** The data shows dearer listings have fewer estimated nights, but busy listings may simply be cheaper for other reasons. We show the pattern, not a demand curve.
- **Interview Q:** *"Can your tool tell a host whether to raise the price?"* **A:** "Not causally. It shows what comparable listings at that price level earn, with a range and warnings; an experiment or the host's own booking data would be needed for elasticity."
- **Where:** `src/revenue_calculator.py`, `tests/test_v2.py`.

### 19. Scenario analysis under unknowns
- **What/why:** The 90-night cap scenario cannot know which listings are second homes, so it parametrises the share (5-30%), the pool, displacement (0/50%) and the occupancy scenario, and reports a sensitivity table. Regulation is described only from the official source with an explicit "verify" note.
- **Concept:** scenario vs forecast, sensitivity analysis, stating assumptions, separating facts you can cite from numbers you assume.
- **Plain explanation:** When a key input is unknowable, don't pick one value; show how the answer moves across plausible values.
- **Interview Q:** *"How did you deal with the missing second-home flag?"* **A:** "Made it an explicit assumption, defined a plausible pool, swept the share, and presented results as ranges with the ranking across districts as the more robust finding."
- **Where:** `src/scenario_cap.py`, `docs/REGULATION_SCENARIO.md`.

### 20. Engineering detail: pickling and entry points
- **What/why:** Running `python -m src.price_model` stores the baseline class as `__main__.MedianBaseline`, which fails to load elsewhere (V3). The entry point now re-imports the module so it pickles as `src.price_model.MedianBaseline`; a test loads the bundle.
- **Concept:** pickle stores a class by module path, not by code.
- **Interview Q:** *"Why did unpickling fail?"* **A:** "The object was serialised under `__main__`; pickle records the module path, so another process cannot find it. Define classes in importable modules."
- **Where:** `src/price_model.py` (bottom), `tests/test_v2.py::test_model_bundle_predicts_sensible_prices`.
