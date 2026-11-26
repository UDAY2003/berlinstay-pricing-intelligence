# Changelog

## Live deployment (2026-11-26)
- App deployed on Streamlit Community Cloud: https://uday2003-berlinstay-pricing-intelligenc-appstreamlit-app-r7kuvt.streamlit.app/. All four tabs checked on the live URL; model output identical to local.

## Release polish (2026-11-26)
- All outputs committed: the 11 SQL result tables in `reports/analysis_tables/`, `reports/README.md`, generated dbt lineage diagram (`docs/DBT_LINEAGE.md`).
- README: results gallery (11 charts, each captioned with its finding), refreshed app screenshots trimmed to content and produced by `scripts/capture_screenshots.py`, verification table.
- App: "Try to break it" panel shows the SQL safety layer live (blocked attacks vs allowed queries); numbers formatted in tables.
- No built-in AI model names in code or docs (model id is supplied by the user); tests check docs links, screenshots and published text. 117 tests; CI green on GitHub.

## Final quality pass (2026-11-26)
- Evaluation: `--preflight`, no report if every call fails at the provider, `score_questions()` refactor, end-to-end harness test with a perfect and a junk model; cost estimate (about 50k input tokens per run).
- Power BI: reference values for all 30 DAX measures (`src/powerbi_expected.py`, `docs/POWERBI_EXPECTED_VALUES.md`, `tests/test_powerbi_measures.py`); guide now warns about the German-locale CSV import pitfall (set locale to English (United States)) and adds date-table checks.
- Ask the data: demo mode shows a validated example immediately; retaken screenshots.
- CI workflow (runs on a clean environment with app requirements only; dry-run locally: 66 pass, 29 skip), LICENSE (MIT, data stays CC BY 4.0), `.gitattributes`, `scripts/check.sh|ps1`, README rewrite with architecture diagram. 95 tests.

## Post-v3.0 fixes and verification (2026-11-23)
- Event windows verified against official sources and corrected: ITB is 16-18 Mar 2027 (was wrongly 2-4 Mar), Berlinale 10-21 Feb 2027, Pride parade 24 Jul 2027, Easter = Good Friday to Easter Monday; Festival of Lights (9-18 Oct 2026) and Marathon (27 Sep 2026) confirmed. Uplift numbers updated (Easter +5.2 pp, ITB -0.1, Pride -1.5); all event rows now `is_indicative = false`.
- `is_benchmark` NULL bug fixed in the V1 SQL as well (it leaked NULLs into the Power BI exports); V1 and dbt now reconcile 19 of 19.
- Pricing-gap bands made strict (below < -20%, above > 20%) so labels match definitions.
- New `tests/test_powerbi_exports.py` recomputes every reconciliation number in the Power BI guide from the exported CSVs (data files verified; DAX itself not executed - Power BI is not installed here).
- LLM client reports provider error codes. 91 tests.

## v3.0 - AI Pricing Assistant (2026-11-23)
- Streamlit app `app/streamlit_app.py`: Market Explorer (map, charts), Price Estimator (V2 model + revenue what-if), Scenario Simulator (night cap), Ask the data.
- Text-to-SQL (`src/text2sql/`): provider-agnostic LLM client (env vars / Streamlit secrets, key never logged), schema context, one self-repair step, safety layer (parser-validated single SELECT, table allow-list, function deny-list, row limit, timeout, locked in-memory DuckDB without file access).
- Evaluation: 42 questions (`eval/questions.jsonl`), `python -m eval.run_eval`, `docs/EVAL.md`. LLM accuracy not yet measured (no API key); 36 adversarial SQL tests and gold-SQL validation done.
- Deployable sample `app/data` (2.3 MB, opaque listing ids), `app/requirements.txt`, `docs/DEPLOY.md`, `docs/CASE_STUDY.md`, `docs/CV_BULLETS.md`; 85 tests.
- Fixes found while building V3: blank last row in `neighbourhoods.csv` created a junk `dim_neighbourhood` member (fixed in V1 SQL and dbt, DQ check and dbt not_null tests added; dbt now 73 nodes); baseline class moved to `src/baseline.py` so the model loads without shap; `.gitignore` anchored so `app/data` is tracked and secrets are ignored anywhere.

## v2.0 - Pricing and Scenarios (2026-11-23)
- dbt-duckdb project (`dbt_project/`): staging -> intermediate -> marts + analysis, seeds for assumptions/events, 71 nodes incl. unique / not_null / accepted_values / relationships tests and business-rule tests; `dbt docs generate` supported.
- V1 vs dbt reconciliation (`docs/V1_V2_RECONCILIATION.md`): 18 of 19 tables identical at v2.0; `is_benchmark` NULL-vs-FALSE bug found by a dbt test (fixed in V1 SQL afterwards, now 19 of 19).
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
