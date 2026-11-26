"""Step 4: export tidy tables for Power BI and other tools.

data/exports/  : CSV + Parquet of every mart table and analysis table (git-ignored, regenerated)
powerbi/       : small UTF-8 (BOM) CSVs + geojson that the Power BI guide loads (committed)
Privacy: host_key (hashed host id) is dropped; no names, descriptions, URLs or review text exist in the model.
"""
import shutil
import duckdb
from src.config import DB_PATH, EXPORT_DIR, POWERBI_DIR, GEOJSON, ROOT

MART_TABLES = {                      # table -> SQL used for export
    "dim_neighbourhood": "SELECT * FROM mart.dim_neighbourhood",
    "dim_host_type": "SELECT * FROM mart.dim_host_type",
    "dim_date": "SELECT * FROM mart.dim_date WHERE year >= 2015",
    "dim_listing": "SELECT * EXCLUDE (host_key) FROM mart.dim_listing",
    "fact_listing": "SELECT * FROM mart.fact_listing",
    "fact_review_month": "SELECT f.* FROM mart.fact_review_month f WHERE f.month_start >= DATE '2015-01-01'",
    "fact_availability_week": "SELECT * FROM mart.fact_availability_week",
}
POWERBI_ANALYSIS = ["monthly_review_series", "seasonal_index", "forward_availability_weekly",
                    "forward_availability_events", "review_demand_trends", "neighbourhood_summary"]


def export(db_path=DB_PATH) -> dict:
    (EXPORT_DIR / "analysis").mkdir(parents=True, exist_ok=True)
    POWERBI_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    counts = {}
    for name, sql in MART_TABLES.items():
        df = con.execute(f"SELECT * FROM ({sql}) ORDER BY ALL").df()      # deterministic row order: rebuilds give identical files
        df.to_csv(EXPORT_DIR / f"{name}.csv", index=False, encoding="utf-8")
        df.to_parquet(EXPORT_DIR / f"{name}.parquet", index=False)
        df.to_csv(POWERBI_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
        counts[name] = len(df)
    analysis = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='analysis'").fetchall()]
    for name in analysis:
        df = con.execute(f"SELECT * FROM analysis.{name} ORDER BY ALL").df()
        df.to_csv(EXPORT_DIR / "analysis" / f"{name}.csv", index=False, encoding="utf-8")
        (ROOT / "reports" / "analysis_tables").mkdir(parents=True, exist_ok=True)
        df.to_csv(ROOT / "reports" / "analysis_tables" / f"{name}.csv", index=False, encoding="utf-8")   # committed copy of every SQL answer
        if name in POWERBI_ANALYSIS:
            df.to_csv(POWERBI_DIR / f"analysis_{name}.csv", index=False, encoding="utf-8-sig")
        counts[f"analysis.{name}"] = len(df)
    if GEOJSON.exists():
        shutil.copy(GEOJSON, POWERBI_DIR / "neighbourhoods.geojson")
    for name, n in counts.items():
        print(f"exported {name}: {n:,} rows")
    return counts


if __name__ == "__main__":
    export()
