"""BerlinStay Pricing Intelligence - V3 Streamlit app.

Tabs: Market Explorer | Price Estimator | Scenario Simulator | Ask the data (safe text-to-SQL).
Data: app/data/*.parquet (small sample, opaque listing ids). Credit: Inside Airbnb (insideairbnb.com), CC BY 4.0.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.predict import load_bundle, predict, capacity_band
from src.revenue_calculator import RevenueCalculator, Profile
from src.scenario_cap import run as run_cap
from src.text2sql.engine import ask
from src.text2sql.llm import get_provider, ProviderError
from src.text2sql.safety import make_connection, execute_safe
from src.text2sql.schema import ALLOWED_TABLES

DATA = ROOT / "app" / "data"
BLUE, GREY = "#2a6f97", "#8d99ae"
st.set_page_config(page_title="BerlinStay Pricing Intelligence", page_icon=":house:", layout="wide")


# ---------------------------------------------------------------- cached resources
@st.cache_resource
def get_con():
    return make_connection(DATA)


@st.cache_resource
def get_bundle():
    return load_bundle(ROOT / "app" / "model" / "price_model.joblib")


@st.cache_resource
def get_geojson():
    return json.loads((DATA / "neighbourhoods.geojson").read_text(encoding="utf-8"))


def q(sql, params=None) -> pd.DataFrame:
    cur = get_con().cursor()
    try:
        return cur.execute(sql, params or []).df()
    finally:
        cur.close()


@st.cache_data
def benchmark_frame() -> pd.DataFrame:
    return q("""SELECT f.listing_id, n.district, d.room_type, d.capacity_band, d.license_status, d.host_type_key, f.price_eur,
                       f.number_of_reviews_ltm, f.est_nights_low, f.est_nights_base, f.est_nights_high
                FROM fact_listing f JOIN dim_listing d USING (listing_id)
                JOIN dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key WHERE d.is_benchmark""")


@st.cache_data
def neighbourhood_table() -> pd.DataFrame:
    return q("""SELECT n.district, n.neighbourhood, MEDIAN(d.latitude) AS latitude, MEDIAN(d.longitude) AS longitude, COUNT(*) AS n
                FROM dim_listing d JOIN dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key
                WHERE d.is_benchmark GROUP BY 1, 2""")


def provider_or_none():
    try:
        secrets = st.secrets if len(st.secrets) else None
    except Exception:
        secrets = None
    try:
        return get_provider(secrets=secrets)
    except ProviderError as e:
        st.warning(str(e))
        return None


def footer():
    st.caption("Data: Inside Airbnb (insideairbnb.com), Berlin, scraped 19 Sep 2026, CC BY 4.0 - not affiliated with Airbnb. "
               "Occupancy and revenue are ESTIMATES from a review-based model; the calendar cannot separate booked from blocked nights; "
               "locations are anonymised (~150 m); one snapshot; listing ids in this app are opaque. Not legal, tax or investment advice.")


st.title("BerlinStay Pricing Intelligence")
st.caption("How should a Berlin host price a listing, what income is realistic, and how do seasonality and local rules change that?")
TAB_NAMES = ["Market Explorer", "Price Estimator", "Scenario Simulator", "Ask the data"]
_sel = st.query_params.get("tab")                    # deep link: ?tab=Price%20Estimator
tab1, tab2, tab3, tab4 = st.tabs(TAB_NAMES, default=_sel if _sel in TAB_NAMES else None)

# ================================================================ 1. Market Explorer
with tab1:
    c1, c2, c3 = st.columns(3)
    rooms = c1.multiselect("Room type", ["Entire home/apt", "Private room", "Hotel room", "Shared room"], default=["Entire home/apt", "Private room"])
    districts = c2.multiselect("District", sorted(q("SELECT DISTINCT district FROM dim_neighbourhood").district), default=[])
    bands = c3.multiselect("Guest capacity", ["1-2", "3-4", "5-6", "7+"], default=[])
    where, params = ["d.is_benchmark"], []
    for col, vals in (("d.room_type", rooms), ("n.district", districts), ("d.capacity_band", bands)):
        if vals:
            where.append(f"{col} IN ({','.join('?' * len(vals))})")
            params += vals
    W = " AND ".join(where)
    base = f"FROM fact_listing f JOIN dim_listing d USING (listing_id) JOIN dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key WHERE {W}"
    k = q(f"SELECT COUNT(*) AS n, MEDIAN(f.price_eur) AS p, MEDIAN(f.est_revenue_base) AS r, quantile_cont(f.price_eur, 0.25) AS p25, quantile_cont(f.price_eur, 0.75) AS p75 {base}", params).iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Benchmark listings", f"{int(k.n):,}")
    m2.metric("Median price / night", f"{k.p:,.0f} EUR" if k.n else "-")
    m3.metric("Middle half of prices", f"{k.p25:,.0f}-{k.p75:,.0f} EUR" if k.n else "-")
    m4.metric("Median est. revenue / year", f"{k.r:,.0f} EUR" if k.n else "-", help="ESTIMATE: nights from a review-rate model x listed price, gross")
    st.caption("Benchmark = priced, short-stay (<28 nights), price 10-1,000 EUR (6,456 of 12,376 listings).")
    if k.n:
        left, right = st.columns([3, 2])
        mp = q(f"SELECT n.neighbourhood, MEDIAN(f.price_eur) AS median_price, COUNT(*) AS listings {base} GROUP BY 1 HAVING COUNT(*) >= 20", params)
        fig = px.choropleth(mp, geojson=get_geojson(), locations="neighbourhood", featureidkey="properties.neighbourhood", color="median_price",
                            color_continuous_scale="YlGnBu", hover_data={"listings": True}, labels={"median_price": "EUR / night"})
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=430, title="Median price by Ortsteil (areas with at least 20 listings)")
        left.plotly_chart(fig, width="stretch")
        dd = q(f"SELECT n.district, MEDIAN(f.price_eur) AS median_price, COUNT(*) AS listings {base} GROUP BY 1 ORDER BY 2", params)
        fig2 = px.bar(dd, x="median_price", y="district", orientation="h", text="listings", color_discrete_sequence=[BLUE], labels={"median_price": "median EUR / night", "district": ""})
        fig2.update_traces(texttemplate="n=%{text}")
        fig2.update_layout(height=430, margin=dict(l=0, r=0, t=30, b=0), title="Median price by district")
        right.plotly_chart(fig2, width="stretch")
    a, b = st.columns(2)
    si = q("""WITH m AS (SELECT year(month_start) yr, month(month_start) mth, SUM(n_reviews) r FROM fact_review_month WHERE year(month_start) BETWEEN 2023 AND 2025 GROUP BY 1,2),
              s AS (SELECT yr, mth, r / SUM(r) OVER (PARTITION BY yr) AS share FROM m)
              SELECT mth, strftime(make_date(2000, mth, 1), '%b') AS month, AVG(share) * 12 AS seasonal_index FROM s GROUP BY mth ORDER BY mth""")
    f3 = px.bar(si, x="month", y="seasonal_index", color_discrete_sequence=[BLUE], title="Seasonality: review index 2023-2025 (1.0 = average month)")
    f3.add_hline(y=1, line_dash="dot")
    f3.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
    a.plotly_chart(f3, width="stretch")
    mr = q("SELECT month_start, SUM(n_reviews) AS reviews FROM fact_review_month WHERE month_start BETWEEN DATE '2015-01-01' AND DATE '2026-08-01' GROUP BY 1 ORDER BY 1")
    mr["rolling_12m"] = mr.reviews.rolling(12).mean()
    f4 = px.line(mr, x="month_start", y=["reviews", "rolling_12m"], title="Reviews per month (demand proxy; dip = COVID-19)", color_discrete_sequence=[GREY, BLUE])
    f4.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0), legend_title="")
    b.plotly_chart(f4, width="stretch")
    st.info("Seasonality comes from review dates (reviews follow stays, so peaks lag by about a month). This data release has no calendar prices, so a price premium for seasons or events cannot be measured.")
    footer()

# ================================================================ 2. Price Estimator
with tab2:
    st.subheader("Estimate a nightly price and annual revenue range")
    bundle, nt = get_bundle(), neighbourhood_table()
    nt = nt[nt.neighbourhood.isin(bundle["categories"]["neighbourhood"])]
    c1, c2, c3 = st.columns(3)
    room = c1.selectbox("Room type", ["Entire home/apt", "Private room", "Hotel room", "Shared room"], key="e_room")
    district = c2.selectbox("District", sorted(nt.district.unique()), key="e_dist")
    hood = c3.selectbox("Neighbourhood (Ortsteil)", sorted(nt[nt.district == district].neighbourhood), key="e_hood")
    c1, c2, c3, c4 = st.columns(4)
    acc = c1.number_input("Guests", 1, 16, 4)
    bed = c2.number_input("Bedrooms", 0, 10, 1)
    beds = c3.number_input("Beds", 1, 16, 2)
    bath = c4.number_input("Bathrooms", 0.5, 6.0, 1.0, step=0.5)
    c1, c2, c3, c4 = st.columns(4)
    ptype = c1.selectbox("Property type", bundle["categories"]["property_type_grp"], index=bundle["categories"]["property_type_grp"].index("Entire rental unit"))
    amen = c2.slider("Number of amenities listed", 0, 80, 35)
    nlist = c3.number_input("Your total listings", 1, 100, 1)
    superhost = c4.checkbox("Superhost")
    minn = st.slider("Typical minimum stay (nights)", 1, 27, 2)
    ll = nt[(nt.district == district) & (nt.neighbourhood == hood)].iloc[0]
    est = predict(bundle, room_type=room, property_type_grp=ptype, district=district, neighbourhood=hood, latitude=float(ll.latitude), longitude=float(ll.longitude),
                  accommodates=int(acc), bedrooms=int(bed), beds=int(beds), bathrooms=float(bath), amenities_count=int(amen), is_superhost=superhost,
                  host_listings_count=int(nlist), minimum_nights_avg=float(minn))
    m1, m2, m3 = st.columns(3)
    m1.metric("Model estimate", f"{est['price']:.0f} EUR / night")
    m2.metric("Approximate range", f"{est['low']:.0f}-{est['high']:.0f} EUR", help="q10-q90 quantile models. On held-out hosts the nominal 80% range covered 72% of listings, so treat it as approximate.")
    m3.metric("District x room-type median (baseline)", f"{est['baseline']:.0f} EUR")
    st.caption("LightGBM on listing attributes, location and host profile; held-out MAE 53.6 EUR vs 66.7 EUR for the median baseline. It predicts asking prices of comparable listings, "
               "not what guests will pay, and cannot see photos, quality or exact micro-location.")
    st.divider()
    st.subheader("What-if: revenue at a price you choose")
    c1, c2, c3 = st.columns(3)
    price = c1.slider("Nightly price (EUR)", 20, 600, int(round(est["price"] / 5) * 5))
    cap = c2.selectbox("Annual night cap", ["none", 90, 120, 180], help="Scenario only. See the Scenario Simulator tab and docs/REGULATION_SCENARIO.md.")
    fee = c3.number_input("Platform fee % (your channel)", 0.0, 30.0, 0.0, step=0.5) / 100
    calc = RevenueCalculator(benchmark_frame())
    prof = Profile(district, room, int(acc), float(price), None if cap == "none" else int(cap), fee)
    e = calc.estimate(prof)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Revenue / year (median)", f"{e.revenue_base:,.0f} EUR", help="ESTIMATE, gross unless a platform fee is set")
    r2.metric("Spread between similar listings", f"{e.revenue_low:,.0f}-{e.revenue_high:,.0f} EUR", help="25th-75th percentile of comparable listings")
    r3.metric("Estimated nights / occupancy", f"{e.nights_base:.0f} / {e.occupancy_base:.0%}")
    r4.metric("Net after fee (indicative)", f"{e.net_base:,.0f} EUR")
    st.caption(f"Comparable set: {e.comparable_set} (n={e.n_comparable}); your price is {e.price_position:.2f}x the comparable median ({e.segment_median_price:.0f} EUR). "
               f"If the occupancy model's assumptions are pessimistic/optimistic the median is {e.revenue_median_model_low:,.0f}/{e.revenue_median_model_high:,.0f} EUR.")
    for w in e.warnings:
        st.warning(w)
    if e.breakeven_price_for_cap:
        st.info(f"With a {cap}-night cap, keeping the same revenue would need about {e.breakeven_price_for_cap:,.0f} EUR per night (ignores guest reaction to higher prices).")
    curve = calc.price_curve(prof, list(range(40, 421, 20)))
    fig = px.line(curve, x="price_eur", y=["revenue_low", "revenue_base", "revenue_high"], labels={"value": "EUR / year", "price_eur": "nightly price"},
                  title="Estimated revenue by price (association in the data, not a measured demand curve)", color_discrete_sequence=[GREY, BLUE, "#e07a1f"])
    fig.update_layout(height=340, legend_title="", margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, width="stretch")
    footer()

# ================================================================ 3. Scenario Simulator
with tab3:
    st.subheader("Scenario: an annual night cap on self-used second homes")
    st.error("SCENARIO, not a forecast and not legal advice. The data cannot identify second homes, so the share below is YOUR assumption. "
             "Berlin's official Senate page (berlin.de/sen/wohnen/rechtliches/zweckentfremdungsverbot/) refers to a self-used second home rented at most 90 days a year and to a 2026 "
             "amendment; verify scope and dates on official sources.")
    c1, c2, c3, c4 = st.columns(4)
    capn = c1.slider("Cap (nights per year)", 30, 180, 90, step=10)
    share = c2.slider("Share of single-host entire homes that are capped second homes (%)", 0, 50, 20, step=5) / 100
    disp = c3.slider("Share of lost nights re-booked elsewhere (%)", 0, 100, 0, step=10) / 100
    occ = c4.selectbox("Occupancy model scenario", ["base", "low", "high"])
    dd, city, pool = run_cap(cap=capn, shares=[share], displacement=disp, scenario=occ, df=benchmark_frame())
    cr = city.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pool (single-host entire homes)", f"{int(cr.pool_listings):,}")
    m2.metric("Pool above the cap", f"{(pool.n > capn).mean():.0%}")
    m3.metric("Net revenue affected", f"{cr.net_lost_revenue / 1e6:.1f} EUR m", f"{-cr.pct_of_market_revenue:.1f}% of est. market revenue", delta_color="off")
    m4.metric("Net nights lost / year", f"{cr.net_lost_nights:,.0f}")
    sweep = pd.concat([run_cap(cap=capn, shares=[s / 100], displacement=disp, scenario=occ, df=benchmark_frame())[1] for s in range(0, 55, 5)])
    fig = px.line(sweep, x=sweep.share_second_homes * 100, y="pct_of_market_revenue", markers=True, color_discrete_sequence=[BLUE],
                  labels={"x": "assumed share of pool that is capped (%)", "pct_of_market_revenue": "% of est. market revenue"}, title="Sensitivity to the key unknown")
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, width="stretch")
    t = dd[dd.pool_listings > 0].sort_values("lost_revenue", ascending=False)[["district", "pool_listings", "pool_over_cap_pct", "lost_nights", "lost_revenue"]]
    t["lost_revenue"] = (t.lost_revenue / 1e6).round(2)
    t["pool_over_cap_pct"] = t.pool_over_cap_pct.round(0).astype(int)
    t["lost_nights"] = t.lost_nights.round(0).astype(int)
    st.table(t.rename(columns={"pool_over_cap_pct": "pool over cap %", "lost_revenue": "lost revenue EUR m", "lost_nights": "lost nights"}).set_index("district"))
    st.caption("Assumptions: capped listings keep min(estimated nights, cap) and lose price x (nights - cap); no price response, no change in registrations, no enforcement modelling. Estimates throughout.")
    footer()

# ================================================================ 4. Ask the data
with tab4:
    st.subheader("Ask the data (text-to-SQL)")
    provider = provider_or_none()
    max_q = int(os.environ.get("LLM_MAX_QUESTIONS_PER_SESSION", 15))
    st.session_state.setdefault("n_asked", 0)
    if provider is None:
        st.info("Demo mode: no LLM key is configured, so you can run pre-written example queries through the same safety layer. "
                "Set LLM_PROVIDER and LLM_API_KEY (environment or Streamlit secrets) to ask free-form questions.")
    else:
        st.success(f"LLM assistant active ({provider.name}: {provider.model}). Privacy: only your question and the table schema are sent to the provider, never data rows.")
    st.caption("Safety: one read-only SELECT, allow-listed tables, validated before execution, 200-row limit, 8 s timeout, locked in-memory database with no file access.")
    qs = [json.loads(l) for l in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    demo = [x for x in qs if x["expect"] == "result"]
    question, run_demo = "", False
    if provider is None:
        pick = st.selectbox("Example question", [x["question"] for x in demo])
        run_demo = st.button("Run example")
        question = pick
    else:
        question = st.text_input("Your question", placeholder="e.g. Which district has the most entire homes above 200 EUR per night?", max_chars=500)
        st.caption("Examples: " + " | ".join(x["question"] for x in demo[:3]))
        go = st.button("Ask")
    if (provider is None and run_demo) or (provider is not None and go):
        if provider is None:
            gold = next(x for x in demo if x["question"] == question)["gold_sql"]
            try:
                df, trunc, sql = execute_safe(get_con(), gold, ALLOWED_TABLES)
                res = dict(sql=sql, df=df, truncated=trunc, error=None)
            except Exception as ex:
                res = dict(sql=gold, df=None, truncated=False, error=str(ex))
        elif st.session_state.n_asked >= max_q:
            res = dict(sql=None, df=None, truncated=False, error=f"Session limit of {max_q} questions reached (cost control). Reload the page to start a new session.")
        else:
            st.session_state.n_asked += 1
            with st.spinner("Generating and checking SQL..."):
                a = ask(question, provider, get_con())
            res = dict(sql=a.sql, df=a.df, truncated=a.truncated, error=a.error)
        if res["sql"]:
            st.markdown("**SQL (validated before execution)**")
            st.code(res["sql"], language="sql")
        if res["error"]:
            st.error(res["error"])
        elif res["df"] is not None:
            st.dataframe(res["df"], hide_index=True, width="stretch")
            if res["truncated"]:
                st.caption("Showing the first 200 rows.")
            d = res["df"]
            if d.shape[1] == 2 and 1 < len(d) <= 40 and pd.api.types.is_numeric_dtype(d.iloc[:, 1]) and not pd.api.types.is_numeric_dtype(d.iloc[:, 0]):
                st.bar_chart(d.set_index(d.columns[0]))
    footer()
