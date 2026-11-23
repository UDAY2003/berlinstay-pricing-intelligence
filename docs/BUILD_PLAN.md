# BerlinStay Pricing Intelligence - Build Plan

One evolving repo, three releases. Each release upgrades the previous one.
Business question: *How should a host or small property manager in Berlin price a listing,
what income is realistic, and how do seasonality and local rules change that?*

## Environment inspection (23 Nov 2026)
| Item | Finding | Decision |
|---|---|---|
| Repo | Empty folder, not a git repo | `git init`, branch `main` |
| Python | `python` launcher points to a broken 3.14 stub; Anaconda has 3.13.5; no 3.12 | venv in `./venv` built from Python **3.13.5** (not 3.12). All pins verified on 3.13 |
| Packages | Nothing installed in the venv | Installed and pinned in `requirements.txt` |
| Data | `data/` did not exist | Downloaded all 5 files for scrape **2026-09-19** into `data/raw/` (git-ignored) |
| Network | Downloads from insideairbnb.com worked | No manual download needed |

## What the real data looks like (profiled before designing anything)
- `listings.csv.gz`: 12,376 listings, 90 columns, unique `id`. `price` is text like `$97.00` and is **missing for 4,219 listings (34%)**.
  Those are almost all inactive (mean availability_365 about 23 days, ~2 reviews LTM), so "active listing" = has a price.
- `calendar.csv.gz`: 4,517,243 rows = 12,376 listings x 365 days, **2026-09-19 to 2027-09-19, forward looking only, and NO price column**
  (only `available`, `minimum_nights`, `maximum_nights`). Consequence: seasonality of *price* cannot be measured from this release.
  Seasonality is measured from (a) the history of review dates (demand proxy, 2009-2026) and (b) forward availability by week (booked-or-blocked pressure, cannot separate the two).
- `reviews.csv.gz`: 708,768 reviews 2009-2026 (2026 is partial, ends 20 Sep). Comments are free text and are **not loaded into any model table**.
- Host fields (`host_since`, response rate, total listings) are empty in this scrape. Host type is derived from `calculated_host_listings_count` instead.
- `license` mixes registration numbers, "Exempt", legal-entity names and **private persons' names** -> treated as sensitive: only a derived category is kept, never the raw text.
- Inside Airbnb already ships `estimated_occupancy_l365d` and `estimated_revenue_l365d` (occupancy capped at 255 nights). We build our own, documented estimate and reconcile to theirs.

## Checklist

### V1 - Market Analytics
- [x] Repo inspection, this plan
- [x] Scaffold (git, .gitignore, requirements, layout)
- [x] `src/load_data.py`: raw files -> DuckDB `raw` schema
- [x] `src/dq_report.py`: data-quality report (row counts, nulls, duplicates, price parsing, outliers) -> `docs/DATA_QUALITY_REPORT.md`
- [x] SQL staging + star schema (`sql/01..03`): dim_listing, dim_neighbourhood, dim_date, dim_host_type, fact_listing, fact_listing_day, fact_review_month. Grain + keys in `docs/DATA_MODEL.md`
- [x] SQL analysis pack (`sql/10..17`): price, supply concentration, multi-listing hosts, occupancy/revenue, seasonality, demand trends
- [x] `src/run_pipeline.py`: one command runs load -> DQ -> model -> analysis -> exports
- [x] EDA notebook (`notebooks/01_eda.ipynb`), executed with real outputs
- [x] Exports to `data/exports/` and `powerbi/`
- [x] `docs/POWERBI_GUIDE.md`
- [x] `docs/MEMO_V1.md` (2-page business memo)
- [x] Tests (`tests/`), README, CHANGELOG, LEARNING_NOTES, tag `v1.0`

### V2 - Pricing and Scenarios
- [x] dbt-duckdb project (staging -> intermediate -> marts) + tests + docs; before/after reconciliation with V1
- [x] Feature engineering, baseline (district x room-type median) vs LightGBM/sklearn, CV, MAE/MAPE, SHAP, segment error analysis (honest comparison)
- [x] What-if revenue calculator module
- [x] 90-night cap scenario (labelled scenario, not legal advice; regulation described cautiously)
- [x] Power BI guide V2 pages, memo, README, CHANGELOG, tag `v2.0`

### V3 - AI Pricing Assistant
- [ ] Streamlit app (Market Explorer, Price Estimator, Scenario Simulator, Ask the data)
- [ ] Text-to-SQL with safety layer (read-only, SELECT only, allow-list, timeout, row limit)
- [ ] 30+ question evaluation set + script + failure write-up
- [ ] Streamlit Cloud deploy (small Parquet sample), `docs/DEPLOY.md`
- [ ] `docs/CASE_STUDY.md`, polished README, CV/LinkedIn bullets, tag `v3.0`

## Open questions for the user
None blocking V1. Needed later (V3 only): an LLM API key for the "Ask the data" assistant (provider is configurable via env vars).

## Known data limits (stated in every deliverable)
Occupancy is an estimate (review-rate model); the calendar cannot separate booked from blocked nights;
locations are anonymised (~150 m); the data is a single snapshot; only aggregated results are reported and no host is ever identified.
Data: Inside Airbnb, CC BY 4.0, http://insideairbnb.com/get-the-data/.
