"""Reference values for every DAX measure in docs/POWERBI_GUIDE.md, computed with pandas from the committed powerbi/ CSVs.

Each function mirrors the filter context of the DAX measure (benchmark filter, ALL() removals, date shifts). Two scenarios:
  A = no slicer, B = slicers room_type = 'Entire home/apt' and district = 'Mitte'.
Writes docs/POWERBI_EXPECTED_VALUES.md. This validates the measure LOGIC and the data files; it does not execute DAX.
"""
import numpy as np
import pandas as pd
from src.config import POWERBI_DIR, DOCS_DIR


def rd(n):
    return pd.read_csv(POWERBI_DIR / f"{n}.csv", encoding="utf-8-sig")


def load():
    f, d, n, h = rd("fact_listing"), rd("dim_listing"), rd("dim_neighbourhood"), rd("dim_host_type")
    m = f.merge(d.drop(columns=["neighbourhood_key", "host_type_key"]), on="listing_id").merge(n, on="neighbourhood_key").merge(h, on="host_type_key")
    return m, rd("fact_price_gap"), rd("fact_review_month"), rd("fact_availability_week"), rd("scenario_cap_sensitivity"), n


def pct(s, q):                      # PERCENTILE.INC == linear interpolation
    return float(np.percentile(s.dropna(), q * 100))


def measures(m, gap, rev, avail, scen, hood, room=None, district=None):
    ctx = m
    if room:
        ctx = ctx[ctx.room_type == room]
    if district:
        ctx = ctx[ctx.district == district]
    b = ctx[ctx.is_benchmark]
    city_b = (m[m.room_type == room] if room else m)[lambda x: x.is_benchmark]      # ALL(dim_neighbourhood) keeps the room_type slicer
    all_hosts_b = ctx[ctx.is_benchmark]                                                # Listings Share: ALL(dim_host_type) only
    out = {}
    out["All Listings"] = len(ctx)
    out["Benchmark Listings"] = len(b)
    out["Benchmark Share %"] = len(b) / len(ctx)
    out["Median Price"] = b.price_eur.median()
    out["Price P25"], out["Price P75"] = pct(b.price_eur, .25), pct(b.price_eur, .75)
    out["Median Est. Revenue (Base)"] = b.est_revenue_base.median()
    out["Median Est. Revenue (Low)"] = b.est_revenue_low.median()
    out["Median Est. Revenue (High)"] = b.est_revenue_high.median()
    out["Median Est. Nights"] = b.est_nights_base.median()
    out["Avg Est. Occupancy %"] = b[b.number_of_reviews_ltm > 0].est_occupancy_rate_base.mean()
    out["Zero-Review Share %"] = (b.number_of_reviews_ltm == 0).mean()
    out["Price Index vs City"] = b.price_eur.median() / city_b.price_eur.median()
    out["Total Est. Revenue (EUR m)"] = b.est_revenue_base.sum() / 1e6
    total_all = (m[m.room_type == room] if room else m)[lambda x: x.is_benchmark].est_revenue_base.sum() / 1e6     # ALL(host_type), ALL(neighbourhood)
    out["Revenue Share % (of all districts/host types in slicer)"] = b.est_revenue_base.sum() / 1e6 / total_all
    out["Registration-Number Share %"] = (b.license_status == "registration_number").mean()
    # --- reviews (month axis; listing slicers flow through dim_listing -> fact_review_month) ---
    ids = set(ctx.listing_id)
    r = rev[rev.listing_id.isin(ids)]
    mon = lambda y, mth: int(r[r.month_start == f"{y}-{mth:02d}-01"].n_reviews.sum())
    out["Reviews (Jul 2026)"] = mon(2026, 7)
    out["Reviews Prior Year (Jul 2025)"] = mon(2025, 7)
    out["Reviews YoY % (Jul 2026)"] = mon(2026, 7) / mon(2025, 7) - 1
    window = pd.date_range("2025-08-01", "2026-07-01", freq="MS").strftime("%Y-%m-%d")
    out["Reviews Rolling 12M (sum, to Jul 2026)"] = int(r[r.month_start.isin(window)].n_reviews.sum())
    # --- forward availability (benchmark listings only by construction) ---
    nk = set(hood[hood.district == district].neighbourhood_key) if district else None
    a = avail[avail.room_type == room] if room else avail
    if nk is not None:
        a = a[a.neighbourhood_key.isin(nk)]
    out["Unavailable % (forward, all weeks)"] = a.unavailable_days.sum() / a.listing_days.sum()
    # --- V2: pricing gaps (fact_price_gap only holds benchmark listings; DAX filters dim_listing[is_benchmark] for predicted price) ---
    g = gap[gap.listing_id.isin(ids)]
    gb = g.merge(ctx[["listing_id"]], on="listing_id")
    out["Median Predicted Price"] = g.pred_price_model.median()
    out["Median Gap EUR"] = g.gap_eur.median()
    out["Median Gap %"] = g.gap_pct.median()
    out["Share Priced Above Model %"] = (g.pricing_position == "above model (>20% over)").mean()
    out["Share Priced Below Model %"] = (g.pricing_position == "below model (>20% under)").mean()
    out["Model MAE EUR"] = g.gap_eur.abs().mean()
    out["Baseline MAE EUR"] = (g.price_eur - g.pred_price_baseline).abs().mean()
    return out


def scenario_value(scen):
    r = scen[(scen.share_second_homes == 0.2) & (scen.occupancy_scenario == "base") & (scen.displacement == 0.0)].iloc[0]
    return r.net_lost_revenue / 1e6


def compute():
    m, gap, rev, avail, scen, hood = load()
    A = measures(m, gap, rev, avail, scen, hood)
    B = measures(m, gap, rev, avail, scen, hood, room="Entire home/apt", district="Mitte")
    A["Scenario Lost Revenue EUR m (20%, base, no displacement)"] = scenario_value(scen)
    ht = m[m.is_benchmark].groupby("host_type").agg(n=("listing_id", "size"), rev=("est_revenue_base", "sum"))
    ht["Listings Share %"], ht["Revenue Share %"] = ht.n / ht.n.sum(), ht.rev / ht.rev.sum()
    return A, B, ht


def fmt(v):
    if isinstance(v, str):
        return v
    if abs(v) < 1.5 and v != 0 and not float(v).is_integer():
        return f"{v:.4f}"
    return f"{v:,.2f}" if not float(v).is_integer() else f"{int(v):,}"


def main():
    A, B, ht = compute()
    L = ["# Power BI expected values (reference for your dashboard)", "",
         "Every measure in `docs/POWERBI_GUIDE.md`, recomputed with pandas from the CSVs in `powerbi/`, mirroring each measure's filter context. "
         "Use it to check your dashboard: put each measure in a **Card**, then apply the slicers. Generated by `python -m src.powerbi_expected` "
         "(and asserted in `tests/test_powerbi_measures.py`). This verifies the logic and the data files; it does not run DAX.", "",
         "- **Scenario A:** no slicers.", "- **Scenario B:** slicers `room_type = Entire home/apt` and `district = Mitte`.",
         "- Percent measures are shown as fractions (format as % in Power BI). `Reviews*` use the month axis (Jul 2026 / Aug 2025-Jul 2026).", "",
         "| Measure | A: no slicer | B: Entire home + Mitte |", "|---|---|---|"]
    for k in A:
        L.append(f"| {k} | {fmt(A[k])} | {fmt(B[k]) if k in B else '-'} |")
    L += ["", "## Per host type (Scenario A, visual: host_type on the axis)", "", "| host_type | Benchmark listings | Listings Share % | Revenue Share % |", "|---|---|---|---|"]
    L += [f"| {i} | {int(r.n):,} | {r['Listings Share %']:.4f} | {r['Revenue Share %']:.4f} |" for i, r in ht.iterrows()]
    (DOCS_DIR / "POWERBI_EXPECTED_VALUES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
