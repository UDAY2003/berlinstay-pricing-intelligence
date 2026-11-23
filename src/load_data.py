"""Step 1: load raw Inside Airbnb files into DuckDB (schema `raw`). No cleaning here.

Raw tables keep every source column untouched so the pipeline is auditable.
`reviews.comments` (free text) and personal-ish text are dropped from the raw review table
because no analysis needs them and reviews contain third-party personal text.
"""
import sys
import duckdb
from src.config import DB_PATH, RAW_FILES


def load(db_path=DB_PATH) -> None:
    missing = [str(p) for p in RAW_FILES.values() if not p.exists()]
    if missing:
        sys.exit("Missing raw files, download them into data/raw/ first:\n  " + "\n  ".join(missing))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # sample_size=-1 -> read whole file to infer types (listings has sparse columns)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.listings AS
        SELECT * FROM read_csv('{RAW_FILES['listings'].as_posix()}', sample_size=-1)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.calendar AS
        SELECT * FROM read_csv('{RAW_FILES['calendar'].as_posix()}', sample_size=-1)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.reviews AS
        SELECT listing_id, id AS review_id, date AS review_date
        FROM read_csv('{RAW_FILES['reviews'].as_posix()}', sample_size=-1)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.neighbourhoods AS
        SELECT * FROM read_csv('{RAW_FILES['neighbourhoods'].as_posix()}', encoding='utf-8')""")
    for t in ("listings", "calendar", "reviews", "neighbourhoods"):
        n = con.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0]
        print(f"raw.{t}: {n:,} rows")
    con.close()


if __name__ == "__main__":
    load()
