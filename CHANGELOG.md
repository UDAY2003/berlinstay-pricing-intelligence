# Changelog

## v3.0 - AI Pricing Assistant (2026-11-23)
- Streamlit app `app/streamlit_app.py`: Market Explorer (map, charts), Price Estimator (V2 model + revenue what-if), Scenario Simulator (night cap), Ask the data.
- Text-to-SQL (`src/text2sql/`): provider-agnostic LLM client (env vars / Streamlit secrets, key never logged), schema context, one self-repair step, safety layer (parser-validated single SELECT, table allow-list, function deny-list, row limit, timeout, locked in-memory DuckDB without file access).
- Evaluation: 42 questions (`eval/questions.jsonl`), `python -m eval.run_eval`, `docs/EVAL.md`. LLM accuracy not yet measured (no API key); 36 adversarial SQL tests and gold-SQL validation done.
- Deployable sample `app/data` (2.3 MB, opaque listing ids), `app/requirements.txt`, `docs/DEPLOY.md`, `docs/CASE_STUDY.md`, `docs/CV_BULLETS.md`; 85 tests.
- Fixes found while building V3: blank last row in `neighbourhoods.csv` created a junk `dim_neighbourhood` member (fixed in V1 SQL and dbt, DQ check and dbt not_null tests added; dbt now 73 nodes); baseline class moved to `src/baseline.py` so the model loads without shap; `.gitignore` anchored so `app/data` is tracked and secrets are ignored anywhere.

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
