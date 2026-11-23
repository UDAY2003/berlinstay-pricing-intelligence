# BerlinStay Pricing Intelligence

> How should a host or small property manager in Berlin price a listing, what income is realistic, and how do seasonality and local rules change that?

One evolving portfolio project built in three releases on public Inside Airbnb data for Berlin.

| Release | Status | Content |
|---|---|---|
| **V1 Market Analytics** | done (v1.0) | DuckDB star schema, SQL analysis pack, data-quality report, EDA notebook, Power BI guide, business memo |
| **V2 Pricing and Scenarios** | **done (v2.0)** | dbt-duckdb models and tests, LightGBM price model vs median baseline, revenue what-if, 90-night-cap scenario |
| **V3 AI Pricing Assistant** | **done (v3.0)** | Streamlit app (market explorer, price estimator, scenario simulator) and a guarded text-to-SQL "Ask the data" assistant |

**Live app:** _placeholder: add your Streamlit Community Cloud URL after deploying ([steps](docs/DEPLOY.md))_

| Market Explorer | Price Estimator | Scenario Simulator | Ask the data |
|---|---|---|---|
| _screenshot placeholder_ | _screenshot placeholder_ | _screenshot placeholder_ | _screenshot placeholder_ |

Charts from the analysis are in [`docs/img/`](docs/img). Case study: [docs/CASE_STUDY.md](docs/CASE_STUDY.md).

## Key findings (V1, estimates where stated)
- Only **52%** of 12,376 listings are priced short-stay listings (6,456); 34% have no price and 13.5% are mid-term (28+ nights).
- Median nightly price: **181 EUR** entire home (middle half 135-256), **91 EUR** private room; Mitte highest (205 for entire homes), Reinickendorf lowest (115).
- Estimated gross income (entire homes, median): **16.8k / 26.0k / 29.1k EUR per year** (low / base / high scenario). Estimates, before fees, taxes and costs.
- Review-based seasonality: strongest in September, July, June, October; weakest in January-February. Review activity Jan-Aug 2026 is +15.4% vs 2025.
- Hosts with 4+ listings: about 10% of hosts, 42% of listings, 47% of estimated revenue.

## Key findings (V2)
- dbt rebuild reproduces V1: 18 of 19 tables identical, one NULL-vs-FALSE bug found by a dbt test ([reconciliation](docs/V1_V2_RECONCILIATION.md)).
- LightGBM price model, tested on hosts it never saw: **MAE 53.6 EUR vs 66.7 EUR** for the district x room-type median (95% CI of the difference -15.8 to -10.5). Not better for private rooms or the 150-250 EUR band; 80% interval covers 72% ([report](docs/PRICE_MODEL_REPORT.md)).
- 90-night cap *scenario* (not legal advice): if 20% of single-host entire homes were capped second homes, about 2.6% of estimated market revenue would be affected ([scenario](docs/REGULATION_SCENARIO.md)).

Read the full [business memo](docs/MEMO_V2.md) (V1 version: [MEMO_V1](docs/MEMO_V1.md)).

## Architecture
```
raw CSV (data/raw, git-ignored) -> DuckDB (data/berlinstay.duckdb)
   -> raw -> stg -> mart (star schema) -> analysis      [V1: plain SQL, sql/]
   -> exports (CSV/Parquet) -> Power BI                 [powerbi/, data/exports/]
   -> notebooks/ (pandas, matplotlib read from DuckDB)
   V2: dbt-duckdb replaces the SQL build   V3: Streamlit reads DuckDB
```

## Key findings (V3)
- Streamlit app on a **2.3 MB** committed sample (opaque listing ids, no host or text fields) - deployable on Streamlit Community Cloud ([DEPLOY.md](docs/DEPLOY.md)).
- "Ask the data": the LLM writes SQL but is never trusted. DuckDB's parser must see one SELECT, tables must be allow-listed, the database is in-memory and locked (no file access), with a 200-row limit and 8 s timeout. 36/36 adversarial SQL strings are rejected in tests. Provider is configurable (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`).
- Evaluation harness with 42 questions ready ([docs/EVAL.md](docs/EVAL.md)). **LLM accuracy has not been measured yet** (no API key was available); gold SQL is validated 35/35.

## Run the app
```powershell
source venv/Scripts/activate
pip install -r requirements.txt
python -m src.run_v2 && python -m src.build_app_data   # only needed if you changed data or model (the sample is committed)
streamlit run app/streamlit_app.py
# optional LLM:  $env:LLM_PROVIDER="anthropic"; $env:LLM_API_KEY="..."; then   python -m eval.run_eval --provider env
```

## Reproduce V1
```bash
python -m venv venv && source venv/Scripts/activate      # Windows Git Bash (Python 3.13 used here; 3.12 also fine)
pip install -r requirements.txt
# put the 5 Inside Airbnb files (scrape 2026-09-19) in data/raw/ :
#   listings.csv.gz, calendar.csv.gz, reviews.csv.gz, neighbourhoods.csv, neighbourhoods.geojson
#   https://data.insideairbnb.com/germany/be/berlin/2026-09-19/data/listings.csv.gz  (same folder: calendar, reviews;
#   .../visualisations/neighbourhoods.csv and .geojson)
python -m src.run_pipeline          # load -> star schema -> SQL analysis -> DQ report -> exports (about 25 s)
python -m pytest -q tests           # 85 tests
python -m nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
```

## Reproduce V2
```bash
pip install -r requirements.txt
python -m src.run_v2                                  # V1 pipeline -> dbt build (71 nodes) -> reconciliation -> price model -> scenario -> tests
cd dbt_project && dbt build --profiles-dir . && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .   # model docs and lineage
python -m src.revenue_calculator                      # example what-if
```

## Repo map
| Path | What |
|---|---|
| `sql/` | numbered SQL: `00-03` build (assumptions, staging, dimensions, facts), `10-18` analysis pack |
| `src/` | loader, SQL runner, data-quality report, exports, one-command pipeline |
| `dbt_project/` | V2 dbt-duckdb models, seeds, tests |
| `src/features.py`, `src/price_model.py`, `models/` | V2 features, model training, saved model bundle |
| `src/revenue_calculator.py`, `src/scenario_cap.py` | V2 what-if tool and cap scenario |
| `app/`, `src/text2sql/`, `src/predict.py` | V3 Streamlit app, safe text-to-SQL, single-listing prediction |
| `eval/`, `docs/EVAL.md` | 42-question evaluation set, scoring script, write-up |
| `docs/DEPLOY.md`, `docs/CASE_STUDY.md`, `docs/CV_BULLETS.md` | deployment steps, case study, CV/LinkedIn drafts |
| `docs/PRICE_MODEL_REPORT.md`, `docs/REGULATION_SCENARIO.md`, `docs/V1_V2_RECONCILIATION.md` | V2 generated reports |
| `notebooks/01_eda.ipynb` | EDA with written takeaways |
| `powerbi/`, `docs/POWERBI_GUIDE.md` | files and step-by-step build guide (DAX, pages, model) |
| `docs/DATA_MODEL.md` | grain, keys, occupancy formula and assumptions |
| `docs/DATA_QUALITY_REPORT.md` | generated checks and findings |
| `docs/MEMO_V1.md` | 2-page memo for hosts and managers |
| `docs/LEARNING_NOTES.md` | concepts and interview Q&A per step |
| `docs/BUILD_PLAN.md`, `CHANGELOG.md` | plan and release notes |

## Honest limits
Occupancy and revenue are **estimates** (review-rate model, reconciled to Inside Airbnb's own estimate). The calendar cannot separate booked from blocked nights and contains **no prices** in this release. Locations are anonymised (~150 m). The data is a single snapshot (19 Sep 2026). Results are aggregated; no host is identified. Nothing here is legal, tax or investment advice; regulatory points must be verified with official sources.

## Data credit
Data: [Inside Airbnb](http://insideairbnb.com/get-the-data/), Berlin, scraped 19 Sep 2026, licensed CC BY 4.0. This project is not affiliated with or endorsed by Inside Airbnb or Airbnb.
