# Changelog

## v2.0 - Pricing and Scenarios (2026-11-23)
- dbt-duckdb project (`dbt_project/`): staging -> intermediate -> marts + analysis, seeds for assumptions/events, 71 nodes incl. unique / not_null / accepted_values / relationships tests and business-rule tests; `dbt docs generate` supported.
- V1 vs dbt reconciliation (`docs/V1_V2_RECONCILIATION.md`): 18 of 19 tables identical; `is_benchmark` NULL-vs-FALSE bug found by a dbt test and documented (V1 left unchanged).
- Price model (`src/features.py`, `src/price_model.py`, `docs/PRICE_MODEL_REPORT.md`): district x room-type median baseline vs LightGBM, host-grouped split and CV, paired bootstrap, SHAP, segment error analysis, quantile interval, out-of-fold pricing gaps. Test MAE 53.6 vs 66.7 EUR; limits reported.
- What-if revenue calculator (`src/revenue_calculator.py`).
- 90-night cap scenario (`src/scenario_cap.py`, `docs/REGULATION_SCENARIO.md`), clearly labelled as a scenario and not legal advice.
- Power BI guide: pages 7 (pricing gaps) and 8 (scenarios); `docs/MEMO_V2.md`; learning notes 13-20.
- `python -m src.run_v2` runs everything; 28 automated tests (`tests/test_pipeline.py`, `tests/test_v2.py`).

## v1.0 - Market Analytics (2026-11-23)
- Data: Inside Airbnb Berlin scrape 2026-09-19 loaded into DuckDB (`python -m src.run_pipeline`, about 25 s).
- Star schema (`dim_listing`, `dim_neighbourhood`, `dim_date`, `dim_host_type`, `fact_listing`, `fact_listing_day`, `fact_review_month`, `fact_availability_week`) with documented grain and keys.
- SQL analysis pack `sql/10-18` (price, supply concentration, multi-listing hosts, occupancy/revenue estimates, seasonality, demand trends, licence field, map-ready summary) using CTEs and window functions.
- Data-quality report (regenerated each run); found and fixed repeated review ids (3,676 ids) and documented the missing calendar prices.
- EDA notebook `notebooks/01_eda.ipynb` (executed), exports to `data/exports/` and `powerbi/`.
- `docs/POWERBI_GUIDE.md`, `docs/MEMO_V1.md`, `docs/DATA_MODEL.md`, `docs/LEARNING_NOTES.md`.
- 20 automated data tests.
