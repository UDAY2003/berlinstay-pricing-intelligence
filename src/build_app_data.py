"""Build the small, committed data sample used by the Streamlit app (app/data/*.parquet).

* Source: dbt marts in data/berlinstay.duckdb (so run `python -m src.run_v2` first)
* Privacy: no host key, no names/text; listing_id is replaced by an OPAQUE surrogate (hash rank) so a row cannot be
  looked up on the platform. The mapping is not stored.
* Excluded on purpose: fact_listing_day (4.5M rows, too big for free hosting); raw review text (never loaded).
"""
import shutil
import duckdb
from src.config import DB_PATH, ROOT, GEOJSON

OUT = ROOT / "app" / "data"
TABLES = {
    "dim_neighbourhood": "SELECT * FROM dbt_mart.dim_neighbourhood",
    "dim_host_type": "SELECT * FROM dbt_mart.dim_host_type",
    "dim_date": "SELECT * FROM dbt_mart.dim_date WHERE year >= 2015",
    "dim_listing": "SELECT * EXCLUDE (host_key) REPLACE (m.new_id AS listing_id) FROM dbt_mart.dim_listing JOIN idmap m USING (listing_id)",
    "fact_listing": "SELECT * EXCLUDE (price_raw, ia_est_occupancy_nights, ia_est_revenue) REPLACE (m.new_id AS listing_id) FROM dbt_mart.fact_listing JOIN idmap m USING (listing_id)",
    "fact_review_month": "SELECT * REPLACE (m.new_id AS listing_id) FROM dbt_mart.fact_review_month JOIN idmap m USING (listing_id) WHERE month_start >= DATE '2015-01-01'",
    "fact_availability_week": "SELECT * FROM dbt_mart.fact_availability_week",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("""CREATE TEMP TABLE idmap AS
        SELECT listing_id, dense_rank() OVER (ORDER BY md5('berlinstay-' || listing_id::VARCHAR)) + 100000 AS new_id
        FROM dbt_mart.dim_listing""")
    for name, sql in TABLES.items():
        if name == "dim_listing":   # idmap join makes new_id ambiguous with listing_id for REPLACE; use explicit form
            sql = ("SELECT m.new_id AS listing_id, d.* EXCLUDE (listing_id, host_key) FROM dbt_mart.dim_listing d JOIN idmap m ON m.listing_id = d.listing_id")
        elif name in ("fact_listing", "fact_review_month"):
            src = {"fact_listing": "dbt_mart.fact_listing", "fact_review_month": "dbt_mart.fact_review_month"}[name]
            excl = " , price_raw, ia_est_occupancy_nights, ia_est_revenue" if name == "fact_listing" else ""
            where = " WHERE f.month_start >= DATE '2015-01-01'" if name == "fact_review_month" else ""
            sql = f"SELECT m.new_id AS listing_id, f.* EXCLUDE (listing_id{excl}) FROM {src} f JOIN idmap m ON m.listing_id = f.listing_id{where}"
        con.execute(f"COPY ({sql}) TO '{(OUT / (name + '.parquet')).as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    gap = ("SELECT m.new_id AS listing_id, g.* EXCLUDE (listing_id) FROM read_csv('" + (ROOT / "powerbi" / "fact_price_gap.csv").as_posix() +
           "') g JOIN idmap m ON m.listing_id = g.listing_id")
    con.execute(f"COPY ({gap}) TO '{(OUT / 'fact_price_gap.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    shutil.copy(GEOJSON, OUT / "neighbourhoods.geojson")
    shutil.copy(ROOT / "models" / "price_model.joblib", ROOT / "app" / "model" / "price_model.joblib")
    total = 0
    for f in sorted(OUT.iterdir()):
        total += f.stat().st_size
        print(f"{f.name:34s} {f.stat().st_size / 1e6:6.2f} MB")
    print(f"total app data {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
