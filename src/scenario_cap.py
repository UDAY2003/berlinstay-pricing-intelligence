"""Scenario: annual night cap (default 90) on self-used second homes. A STYLISED SCENARIO, NOT A LEGAL ASSESSMENT.

The data cannot say which listings are second homes. So the scenario is built from explicit, adjustable assumptions:
  * pool      = entire-home benchmark listings of single-listing hosts (the group where a self-used second home is most plausible)
  * share     = fraction of the pool assumed to be capped second homes (sensitivity 5/10/20/30%; unknown in reality)
  * effect    = a capped listing keeps min(estimated nights, cap) and loses price x (nights - cap)
  * displacement = share of lost nights re-booked by uncapped entire homes in the same district, limited by their spare
                   capacity up to the 255-night model cap (0% and 50% shown)
Numbers are expected values under these assumptions, using the estimated-occupancy model (low/base/high).
Run:  python -m src.scenario_cap
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src.config import ROOT, DOCS_DIR
from src.revenue_calculator import load_benchmark_frame

CAP = 90
SHARES = [0.05, 0.10, 0.20, 0.30]
MODEL_CAP = 255


def run(cap=CAP, shares=SHARES, displacement=0.0, scenario="base", df=None):
    """Return (district table, city table) for one assumption set."""
    df = load_benchmark_frame() if df is None else df
    n = df[f"est_nights_{scenario}"]
    eh = df[df.room_type == "Entire home/apt"].assign(n=n)
    pool = eh[eh.host_type_key == 1].copy()
    pool["lost_nights"] = (pool.n - cap).clip(lower=0)
    pool["lost_rev"] = pool.lost_nights * pool.price_eur
    pool["over_cap"] = pool.n > cap
    tot_rev = float((df.price_eur * n).sum())
    tot_nights = float(n.sum())
    out = []
    for s in shares:
        for district, g in eh.groupby("district"):
            gp = pool[pool.district == district]
            lost_n, lost_r = s * gp.lost_nights.sum(), s * gp.lost_rev.sum()
            unc = g[~g.index.isin(gp.index)]                       # not in pool: always uncapped
            spare = float((MODEL_CAP - unc.n).clip(lower=0).sum() + (1 - s) * (MODEL_CAP - gp.n).clip(lower=0).sum())
            absorbed = min(displacement * lost_n, spare)
            avg_price = float(g.price_eur.mean())
            out.append(dict(share_second_homes=s, district=district, pool_listings=len(gp), pool_over_cap_pct=100 * gp.over_cap.mean() if len(gp) else np.nan,
                            lost_nights=lost_n, lost_revenue=lost_r, absorbed_nights=absorbed, net_lost_nights=lost_n - absorbed,
                            net_lost_revenue=lost_r - absorbed * avg_price))
    d = pd.DataFrame(out)
    city = d.groupby("share_second_homes").agg(pool_listings=("pool_listings", "first"), lost_nights=("lost_nights", "sum"), lost_revenue=("lost_revenue", "sum"),
                                               net_lost_nights=("net_lost_nights", "sum"), net_lost_revenue=("net_lost_revenue", "sum")).reset_index()
    pool_total = len(pool)
    city["pool_listings"] = pool_total
    city["pct_of_market_nights"] = 100 * city.net_lost_nights / tot_nights
    city["pct_of_market_revenue"] = 100 * city.net_lost_revenue / tot_rev
    return d, city, pool


def main():
    df = load_benchmark_frame()
    res = {}
    for sc in ["low", "base", "high"]:
        for disp in (0.0, 0.5):
            d, c, pool = run(displacement=disp, scenario=sc, df=df)
            res[(sc, disp)] = (d, c, pool)
    d0, c0, pool = res[("base", 0.0)]
    d0[d0.share_second_homes == 0.2].to_csv(ROOT / "reports" / "scenario_cap_by_district_base_20pct.csv", index=False)
    sens = pd.concat([c.assign(occupancy_scenario=sc, displacement=disp) for (sc, disp), (_, c, _) in res.items()])
    sens.to_csv(ROOT / "reports" / "scenario_cap_sensitivity.csv", index=False)
    sens.to_csv(ROOT / "powerbi" / "scenario_cap_sensitivity.csv", index=False, encoding="utf-8-sig")
    d0[d0.share_second_homes == 0.2].to_csv(ROOT / "powerbi" / "scenario_cap_by_district_base_20pct.csv", index=False, encoding="utf-8-sig")

    # chart: lost revenue share vs assumed second-home share, three occupancy scenarios (no displacement)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for sc, col in zip(["low", "base", "high"], ["#8d99ae", "#2a6f97", "#e07a1f"]):
        c = res[(sc, 0.0)][1]
        ax.plot(c.share_second_homes * 100, c.pct_of_market_revenue, marker="o", color=col, label=f"{sc} occupancy")
    ax.set(xlabel="assumed share of single-host entire homes that are capped second homes (%)", ylabel="% of estimated market revenue lost",
           title=f"{CAP}-night cap scenario (no displacement)"); ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False); ax.grid(alpha=.25)
    fig.savefig(DOCS_DIR / "img" / "12_cap_scenario.png", bbox_inches="tight", dpi=130); plt.close(fig)

    write_doc(res, pool, df)
    return res


def write_doc(res, pool, df):
    eh = df[df.room_type == "Entire home/apt"]
    n_eh = len(eh)
    base_c = res[("base", 0.0)][1]
    pool_n = len(pool)
    over = 100 * (pool.n > CAP).mean()
    mean_lost_n = pool.lost_nights.mean()
    dd = res[("base", 0.0)][0]
    dd = dd[dd.share_second_homes == 0.2].sort_values("lost_revenue", ascending=False).head(5)
    L = ["# Scenario: a 90-night annual cap on self-used second homes", "",
         "> **This is a clearly labelled SCENARIO, not legal advice and not a forecast.** It asks: *if* a 90-night cap applied to some share of listings, how much estimated "
         "supply and revenue would that touch? The data cannot tell which listings are second homes, so the share is an explicit assumption.", "",
         "## What the rules say (described cautiously - verify official sources)",
         "- Berlin restricts converting residential space to holiday rental under the *Zweckentfremdungsverbot-Gesetz* (ZwVbG). Short-term accommodation units are identified by a **registration number** (a unit-specific identifier).",
         "- The official Senate page (berlin.de/sen/wohnen/rechtliches/zweckentfremdungsverbot/, read 23 Nov 2026) states that a fourth amendment of the ZwVbG, implementing the EU short-term-rental regulation, entered into force in **2026**, and refers to a **self-used Berlin second home rented out for at most 90 days per year**.",
         "- Secondary websites we looked at disagree with each other on who the 90-day limit applies to (some apply it to main residences), so **this project does not rely on them**. Exact scope, exceptions, start dates and fines must be checked on the official page or with the responsible district office.",
         "- The scenario below uses only the narrow reading 'self-used second home, at most 90 nights per year' as a modelling device.", "",
         "## Method (assumptions you can change in `src/scenario_cap.py`)",
         f"- **Pool:** entire-home benchmark listings of single-listing hosts: **{pool_n:,}** of {n_eh:,} entire homes ({100 * pool_n / n_eh:.0f}%). Hosts with several listings are assumed to operate commercially and are outside the pool.",
         "- **Share assumed to be capped second homes:** 5%, 10%, 20%, 30% (unknown; this is the key sensitivity).",
         "- **Effect:** a capped listing keeps `min(estimated nights, 90)` and loses `price x (nights - 90)`. Nights come from the review-based occupancy estimate (low/base/high), so they are estimates.",
         "- **Displacement:** 0% (lost nights vanish) or 50% (half are re-booked by other entire homes in the same district, limited by their spare capacity up to the model's 255-night cap).",
         "- Limits: no price response by hosts or guests, no change in registrations, no enforcement/compliance modelling, snapshot of 19 Sep 2026, and the licence field cannot identify second homes.", "",
         "## Results (base occupancy scenario)", "",
         f"In the pool, **{over:.0f}%** of listings have more than 90 estimated nights per year; the mean estimated nights above the cap per pool listing is **{mean_lost_n:.0f}**.", "",
         "| Assumed capped share | Lost nights/yr (no displacement) | Lost revenue EUR m | % of market est. nights | % of market est. revenue | % revenue lost with 50% displacement |", "|---|---|---|---|---|---|"]
    for s in SHARES:
        r = base_c[base_c.share_second_homes == s].iloc[0]
        r5 = res[("base", 0.5)][1]
        r5 = r5[r5.share_second_homes == s].iloc[0]
        L.append(f"| {int(s * 100)}% | {r.lost_nights:,.0f} | {r.lost_revenue / 1e6:.1f} | {r.pct_of_market_nights:.1f}% | {r.pct_of_market_revenue:.1f}% | {r5.pct_of_market_revenue:.1f}% |")
    L += ["", "### Sensitivity to the occupancy model (20% share, no displacement)", "", "| Occupancy scenario | % of market est. revenue lost |", "|---|---|"]
    for sc in ["low", "base", "high"]:
        c = res[(sc, 0.0)][1]
        L.append(f"| {sc} | {c[c.share_second_homes == 0.2].iloc[0].pct_of_market_revenue:.1f}% |")
    L += ["", "### Districts most affected (base, 20% share, no displacement)", "", "| District | Pool listings | Pool over 90 nights % | Lost revenue EUR m |", "|---|---|---|---|"]
    L += [f"| {r.district} | {r.pool_listings} | {r.pool_over_cap_pct:.0f}% | {r.lost_revenue / 1e6:.2f} |" for r in dd.itertuples()]
    L += ["", "![cap scenario](img/12_cap_scenario.png)", "",
          "## Host-level view", "",
          "A host with a self-used second home earning from 200 nights at a given price would, under a 90-night cap, need a nightly price of about `200/90 = 2.2x` to keep revenue, "
          "which is far above what comparable listings charge. `RevenueCalculator.estimate(Profile(..., max_nights=90))` returns this break-even price and the capped revenue range.", "",
          "## How to read this", "",
          "- The result is an **order of magnitude under stated assumptions**, not a prediction of what the rule does.",
          "- The biggest unknown is the share of second homes; the table shows how fast the answer moves with it.",
          "- Because occupancy is estimated from reviews (and capped at 255 nights), absolute nights are uncertain; the ranking across districts is more reliable than the levels."]
    (DOCS_DIR / "REGULATION_SCENARIO.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
