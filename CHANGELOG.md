# Changelog

## v1.0 - Market Analytics (2026-11-23)
- Data: Inside Airbnb Berlin scrape 2026-09-19 loaded into DuckDB (`python -m src.run_pipeline`, about 25 s).
- Star schema (`dim_listing`, `dim_neighbourhood`, `dim_date`, `dim_host_type`, `fact_listing`, `fact_listing_day`, `fact_review_month`, `fact_availability_week`) with documented grain and keys.
- SQL analysis pack `sql/10-18` (price, supply concentration, multi-listing hosts, occupancy/revenue estimates, seasonality, demand trends, licence field, map-ready summary) using CTEs and window functions.
- Data-quality report (regenerated each run); found and fixed repeated review ids (3,676 ids) and documented the missing calendar prices.
- EDA notebook `notebooks/01_eda.ipynb` (executed), exports to `data/exports/` and `powerbi/`.
- `docs/POWERBI_GUIDE.md`, `docs/MEMO_V1.md`, `docs/DATA_MODEL.md`, `docs/LEARNING_NOTES.md`.
- 20 automated data tests.
