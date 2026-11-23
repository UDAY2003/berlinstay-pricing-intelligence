"""Central paths and constants (all paths are relative to the repo root, via pathlib)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
EXPORT_DIR = ROOT / "data" / "exports"
POWERBI_DIR = ROOT / "powerbi"
SQL_DIR = ROOT / "sql"
DOCS_DIR = ROOT / "docs"
DB_PATH = ROOT / "data" / "berlinstay.duckdb"

SCRAPE_DATE = "2026-09-19"
SOURCE_CREDIT = "Inside Airbnb (insideairbnb.com), CC BY 4.0"

RAW_FILES = {
    "listings": RAW_DIR / "listings.csv.gz",
    "calendar": RAW_DIR / "calendar.csv.gz",
    "reviews": RAW_DIR / "reviews.csv.gz",
    "neighbourhoods": RAW_DIR / "neighbourhoods.csv",
}
GEOJSON = RAW_DIR / "neighbourhoods.geojson"
