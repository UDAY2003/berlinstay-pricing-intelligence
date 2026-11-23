"""Re-computes the Power BI guide's reconciliation numbers from the committed powerbi/ CSVs with pandas (mimicking the DAX measures).
This verifies the DATA FILES and the numbers quoted in docs/POWERBI_GUIDE.md. It does not execute DAX or open Power BI."""
import pandas as pd
import pytest
from src.config import POWERBI_DIR

pytestmark = pytest.mark.skipif(not (POWERBI_DIR / "fact_price_gap.csv").exists(), reason="run `python -m src.run_v2` first")
rd = lambda n: pd.read_csv(POWERBI_DIR / f"{n}.csv", encoding="utf-8-sig")


@pytest.fixture(scope="module")
def m():
    f, d, n = rd("fact_listing"), rd("dim_listing"), rd("dim_neighbourhood")
    return f.merge(d, on="listing_id", suffixes=("", "_d")).merge(n, on="neighbourhood_key")


def test_counts_and_price_medians(m):
    b = m[m.is_benchmark]
    assert len(m) == 12376 and len(b) == 6456                                   # All Listings / Benchmark Listings
    assert round(b.price_eur.median(), 1) == 150.2                              # Median Price
    assert round(b[b.room_type == "Entire home/apt"].price_eur.median()) == 181
    assert round(b[b.room_type == "Private room"].price_eur.median()) == 91
    assert b[(b.room_type == "Entire home/apt") & (b.district == "Mitte")].price_eur.median() == 205


def test_relationships_are_clean(m):
    for t, k in [("fact_listing", "listing_id"), ("dim_listing", "listing_id"), ("fact_price_gap", "listing_id")]:
        assert rd(t)[k].is_unique
    assert set(rd("fact_price_gap").listing_id) <= set(rd("dim_listing").listing_id)
    assert set(rd("fact_review_month").listing_id) <= set(rd("dim_listing").listing_id)
    assert rd("dim_neighbourhood").district.notna().all()
    assert set(rd("fact_availability_week").week_start) <= set(rd("dim_date").date)       # relationship to dim_date[date]
    assert set(rd("fact_review_month").month_start) <= set(rd("dim_date").date)


def test_pricing_gap_measures():
    g = rd("fact_price_gap")
    assert round(100 * (g.pricing_position == "above model (>20% over)").mean(), 1) == 27.8
    assert round(100 * (g.pricing_position == "below model (>20% under)").mean(), 1) == 27.7
    assert round(100 * (g.pricing_position == "in line (within 20%)").mean(), 1) == 44.5
    model_mae = g.gap_eur.abs().mean()
    base_mae = (g.price_eur - g.pred_price_baseline).abs().mean()
    assert 54 <= model_mae <= 56.5 and base_mae > model_mae


def test_scenario_card_value():
    s = rd("scenario_cap_sensitivity")
    r = s[(s.share_second_homes == 0.2) & (s.occupancy_scenario == "base") & (s.displacement == 0.0)].iloc[0]
    assert round(r.net_lost_revenue / 1e6, 1) == 4.3
    assert set(s.occupancy_scenario) == {"low", "base", "high"}


def test_no_sensitive_columns_or_text_in_csv():
    banned = {"host_key", "host_id", "host_name", "name", "description", "license", "comments"}
    for f in POWERBI_DIR.glob("*.csv"):
        assert not (set(pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns) & banned), f.name
