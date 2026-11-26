"""Every DAX measure in the Power BI guide must have a reference value, and key reference values must match the SQL/analysis layer."""
import re
import pytest
from src.config import POWERBI_DIR, DOCS_DIR
from src.powerbi_expected import compute

pytestmark = pytest.mark.skipif(not (POWERBI_DIR / "fact_price_gap.csv").exists(), reason="run `python -m src.run_v2` first")


def guide_measure_names():
    txt = (DOCS_DIR / "POWERBI_GUIDE.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```DAX\n(.*?)```", txt, re.S)
    names = []
    for b in blocks:
        names += re.findall(r"^([A-Za-z][^\n=]*?) =", b, re.M)
    # keep measure definitions only: drop lines from inside measure bodies (they contain '[' or ',') and VAR/RETURN helpers
    return [n.strip() for n in names if "[" not in n and "," not in n and "COUNTROWS" not in n and not n.strip().startswith(("VAR", "RETURN", "CALCULATE", "DIVIDE"))]


def test_every_guide_measure_has_a_reference_value():
    A, B, ht = compute()
    keys = " | ".join(list(A) + ["Listings Share %", "Revenue Share %"])
    names = guide_measure_names()
    assert len(names) >= 25, names
    for n in names:
        base = n.split(" (")[0].strip()
        assert base in keys, f"no reference value for measure '{n}'"


def test_reference_values_match_other_layers():
    A, B, ht = compute()
    assert A["Benchmark Listings"] == 6456 and A["All Listings"] == 12376
    assert round(A["Median Price"], 1) == 150.2 and B["Median Price"] == 205
    # Revenue Share % keeps the room_type slicer in its denominator (ALL() removes only host type and neighbourhood):
    # Mitte entire homes / all entire homes = 38.65 / 138.6
    assert 0.27 < B["Revenue Share % (of all districts/host types in slicer)"] < 0.29
    assert abs(A["Total Est. Revenue (EUR m)"] - 166.02) < 0.01
    assert round(A["Scenario Lost Revenue EUR m (20%, base, no displacement)"], 1) == 4.3
    assert round(A["Share Priced Above Model %"], 3) == 0.278
    assert 0.16 < A["Reviews YoY % (Jul 2026)"] < 0.17                       # same order as the SQL YoY series (16.4% for Jul 2026)
    assert abs(ht["Listings Share %"].sum() - 1) < 1e-9 and abs(ht["Revenue Share %"].sum() - 1) < 1e-9
    assert A["Model MAE EUR"] < A["Baseline MAE EUR"]


def test_reference_review_series_agrees_with_sql_analysis():
    import pandas as pd
    s = pd.read_csv(POWERBI_DIR / "analysis_monthly_review_series.csv", encoding="utf-8-sig")
    row = s[s.month_start == "2026-07-01"].iloc[0]
    A, _, _ = compute()
    assert A["Reviews (Jul 2026)"] == row.reviews and A["Reviews Prior Year (Jul 2025)"] == row.reviews_prev_year
    assert round(A["Reviews YoY % (Jul 2026)"] * 100, 1) == row.yoy_pct
