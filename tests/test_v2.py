"""V2 tests: calculator invariants, scenario monotonicity, model bundle sanity, leakage guard, dbt/V1 agreement."""
import duckdb
import joblib
import numpy as np
import pytest
from sklearn.model_selection import GroupShuffleSplit
from src.config import DB_PATH, ROOT

pytestmark = pytest.mark.skipif(not (DB_PATH.exists() and (ROOT / "models" / "price_model.joblib").exists()),
                                reason="run `python -m src.run_v2` first")


@pytest.fixture(scope="module")
def frame():
    from src.revenue_calculator import load_benchmark_frame
    return load_benchmark_frame()


def test_calculator_ordering_and_formula(frame):
    from src.revenue_calculator import RevenueCalculator, Profile
    e = RevenueCalculator(frame).estimate(Profile("Mitte", "Entire home/apt", 4, 180))
    assert e.nights_low <= e.nights_base <= e.nights_high <= 255
    assert e.revenue_base == round(e.nights_base * 180)
    assert e.revenue_median_model_low <= e.revenue_median_model_high


def test_calculator_cap_reduces_revenue_and_rejects_bad_price(frame):
    from src.revenue_calculator import RevenueCalculator, Profile
    c = RevenueCalculator(frame)
    free = c.estimate(Profile("Mitte", "Entire home/apt", 4, 180))
    capped = c.estimate(Profile("Mitte", "Entire home/apt", 4, 180, max_nights=90))
    assert capped.nights_high <= 90 and capped.revenue_base <= free.revenue_base
    assert capped.breakeven_price_for_cap is not None and capped.breakeven_price_for_cap > 180
    with pytest.raises(ValueError):
        c.estimate(Profile("Mitte", "Entire home/apt", 4, 5000))


def test_calculator_small_segment_falls_back(frame):
    from src.revenue_calculator import RevenueCalculator, Profile
    e = RevenueCalculator(frame).estimate(Profile("Marzahn - Hellersdorf", "Hotel room", 2, 100))
    assert e.n_comparable >= 30 and e.warnings


def test_scenario_monotone_in_share_and_displacement(frame):
    from src.scenario_cap import run
    _, c0, _ = run(displacement=0.0, df=frame)
    _, c5, _ = run(displacement=0.5, df=frame)
    assert c0.net_lost_revenue.is_monotonic_increasing
    assert (c5.net_lost_revenue <= c0.net_lost_revenue + 1e-6).all()
    _, c_hi, _ = run(cap=120, displacement=0.0, df=frame)
    assert (c_hi.lost_revenue <= c0.lost_revenue).all()      # a looser cap removes less revenue


def test_model_bundle_predicts_sensible_prices():
    from src.features import load_model_frame
    b = joblib.load(ROOT / "models" / "price_model.joblib")
    df = load_model_frame().head(300)
    p = np.exp(b["model"].predict(df[b["features"]]))
    assert (p > 10).all() and (p < 1500).all()
    lo, hi = np.exp(b["q10"].predict(df[b["features"]])), np.exp(b["q90"].predict(df[b["features"]]))
    assert (lo <= hi * 1.001).mean() > 0.95


def test_split_has_no_host_leakage():
    from src.features import load_model_frame
    df = load_model_frame()
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(df, df.price_eur, groups=df.host_key))
    assert not (set(df.host_key.iloc[tr]) & set(df.host_key.iloc[te]))


def test_features_exclude_outcome_columns():
    from src.features import LISTING_FEATURES
    assert not any(c in LISTING_FEATURES for c in ["price_eur", "est_revenue_base", "est_nights_base", "number_of_reviews_ltm", "review_scores_rating"])


def test_dbt_marts_match_v1_marts():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for t in ["fact_listing", "dim_neighbourhood", "fact_review_month"]:
        cols = ", ".join(r[0] for r in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema='mart' AND table_name='{t}'").fetchall())
        n = con.execute(f"SELECT COUNT(*) FROM (SELECT {cols} FROM mart.{t} EXCEPT SELECT {cols} FROM dbt_mart.{t})").fetchone()[0]
        assert n == 0, t
