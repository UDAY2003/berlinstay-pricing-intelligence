"""Data-model tests. They run against data/berlinstay.duckdb (build it first: python -m src.run_pipeline)."""
import duckdb
import pytest
import pandas as pd
from src.config import DB_PATH, POWERBI_DIR

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `python -m src.run_pipeline` first")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB_PATH), read_only=True)
    yield c
    c.close()


def one(con, sql):
    return con.execute(sql).fetchone()[0]


# ---- grain / key uniqueness -------------------------------------------------
@pytest.mark.parametrize("table,key", [
    ("dim_listing", "listing_id"), ("fact_listing", "listing_id"), ("dim_neighbourhood", "neighbourhood_key"),
    ("dim_host_type", "host_type_key"), ("dim_date", "date_key"),
])
def test_key_is_unique_and_not_null(con, table, key):
    assert one(con, f"SELECT COUNT(*) FROM mart.{table} WHERE {key} IS NULL") == 0
    assert one(con, f"SELECT COUNT(*) - COUNT(DISTINCT {key}) FROM mart.{table}") == 0


def test_composite_grains(con):
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT (listing_id, date_key)) FROM mart.fact_listing_day") == 0
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT (listing_id, month_start)) FROM mart.fact_review_month") == 0
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT (week_start, neighbourhood_key, room_type)) FROM mart.fact_availability_week") == 0


def test_reviews_deduplicated(con):
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT review_id) FROM stg.reviews") == 0


# ---- referential integrity --------------------------------------------------
@pytest.mark.parametrize("child,col,parent,pcol", [
    ("fact_listing", "listing_id", "dim_listing", "listing_id"),
    ("fact_listing", "neighbourhood_key", "dim_neighbourhood", "neighbourhood_key"),
    ("fact_listing", "host_type_key", "dim_host_type", "host_type_key"),
    ("fact_listing_day", "listing_id", "dim_listing", "listing_id"),
    ("fact_listing_day", "date_key", "dim_date", "date_key"),
    ("fact_review_month", "listing_id", "dim_listing", "listing_id"),
    ("fact_availability_week", "neighbourhood_key", "dim_neighbourhood", "neighbourhood_key"),
])
def test_foreign_keys_resolve(con, child, col, parent, pcol):
    assert one(con, f"SELECT COUNT(*) FROM mart.{child} c LEFT JOIN mart.{parent} p ON c.{col} = p.{pcol} WHERE p.{pcol} IS NULL") == 0


# ---- cleaning rules ---------------------------------------------------------
def test_row_counts_match_source(con):
    assert one(con, "SELECT COUNT(*) FROM mart.dim_listing") == one(con, "SELECT COUNT(*) FROM raw.listings")
    assert one(con, "SELECT COUNT(*) FROM mart.fact_listing_day") == one(con, "SELECT COUNT(*) FROM raw.calendar")


def test_price_parsing_and_outlier_rule(con):
    assert one(con, "SELECT COUNT(*) FROM raw.listings WHERE price IS NOT NULL") == one(con, "SELECT COUNT(*) FROM stg.listings WHERE has_price")
    assert one(con, "SELECT COUNT(*) FROM mart.fact_listing WHERE price_eur NOT BETWEEN 10 AND 1000") == 0
    assert one(con, "SELECT COUNT(*) FROM stg.listings WHERE is_benchmark AND (price_eur IS NULL OR is_mid_term)") == 0


def test_occupancy_never_exceeds_cap_and_scenarios_ordered(con):
    assert one(con, "SELECT MAX(est_nights_high) FROM mart.fact_listing") <= 255
    assert one(con, "SELECT COUNT(*) FROM mart.fact_listing WHERE est_nights_low > est_nights_base OR est_nights_base > est_nights_high") == 0


def test_occupancy_formula_reconciles_with_inside_airbnb(con):
    share = one(con, "SELECT AVG((ABS(est_nights_base - ia_est_occupancy_nights) <= 1)::INT) FROM mart.fact_listing")
    assert share > 0.97


def test_no_sensitive_columns_in_exports():
    banned = {"host_key", "host_id", "host_name", "name", "description", "license", "comments", "reviewer_name", "listing_url"}
    for f in POWERBI_DIR.glob("*.csv"):
        cols = set(pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns)
        assert not (cols & banned), f"{f.name} leaks {cols & banned}"


def test_license_text_is_categorised_only(con):
    allowed = {"registration_number", "exempt", "legal_entity_stated", "person_stated", "other_format", "missing"}
    got = {r[0] for r in con.execute("SELECT DISTINCT license_status FROM mart.dim_listing").fetchall()}
    assert got <= allowed
