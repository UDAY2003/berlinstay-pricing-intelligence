"""Step 2: data-quality report -> docs/DATA_QUALITY_REPORT.md (regenerated from the database on every run).

Checks: row counts, key uniqueness, orphan keys, null rates, price parsing, outliers,
calendar completeness, date ranges, occupancy-formula reconciliation, sensitive-field handling.
"""
import datetime as dt
import duckdb
import pandas as pd
from src.config import DB_PATH, DOCS_DIR, SCRAPE_DATE


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else (f"{v:,.2f}" if isinstance(v, float) else f"{v:,}" if isinstance(v, int) else str(v)) for v in row) + " |")
    return "\n".join(lines)


def build_report(con) -> str:
    q = lambda s: con.execute(s).df()
    out = [f"# Data Quality Report\n\nScrape: Inside Airbnb Berlin, {SCRAPE_DATE}. Generated {dt.date.today()} by `src/dq_report.py` "
           "from the DuckDB `raw` schema. Re-run `python -m src.run_pipeline` to refresh.\n"]

    out.append("## 1. Row counts\n")
    out.append(md_table(q("""
        SELECT 'raw.listings' AS tbl, COUNT(*) AS rows FROM raw.listings UNION ALL
        SELECT 'raw.calendar', COUNT(*) FROM raw.calendar UNION ALL
        SELECT 'raw.reviews', COUNT(*) FROM raw.reviews UNION ALL
        SELECT 'raw.neighbourhoods', COUNT(*) FROM raw.neighbourhoods""")))

    out.append("\n\n## 2. Keys, duplicates and orphans\n")
    out.append(md_table(q("""
        SELECT 'listings: duplicate ids' AS check, COUNT(*) AS n_bad FROM (SELECT id FROM raw.listings GROUP BY id HAVING COUNT(*) > 1) UNION ALL
        SELECT 'reviews: review_id shared by 2+ listings', COUNT(*) FROM (SELECT review_id FROM raw.reviews GROUP BY review_id HAVING COUNT(*) > 1) UNION ALL
        SELECT 'calendar: duplicate (listing, date)', COUNT(*) FROM (SELECT listing_id, cal_date FROM stg.calendar GROUP BY ALL HAVING COUNT(*) > 1) UNION ALL
        SELECT 'calendar: listing_id not in listings', COUNT(DISTINCT listing_id) FROM raw.calendar WHERE listing_id NOT IN (SELECT id FROM raw.listings) UNION ALL
        SELECT 'reviews: listing_id not in listings', COUNT(*) FROM raw.reviews WHERE listing_id NOT IN (SELECT id FROM raw.listings) UNION ALL
        SELECT 'listings: neighbourhood not in neighbourhoods.csv', COUNT(*) FROM mart.dim_listing WHERE neighbourhood_key IS NULL UNION ALL
        SELECT 'listings: no host-type bucket', COUNT(*) FROM mart.dim_listing WHERE host_type_key IS NULL""")))

    out.append("\n\n## 3. Calendar completeness\n")
    cal = q("""SELECT MIN(cal_date) AS first_day, MAX(cal_date) AS last_day, COUNT(DISTINCT listing_id) AS listings,
               COUNT(*) AS rows, ROUND(AVG((NOT is_available)::INT) * 100, 1) AS pct_unavailable
               FROM stg.calendar""")
    out.append(md_table(cal.astype(str)))
    days = q("SELECT days, COUNT(*) AS listings FROM (SELECT listing_id, COUNT(*) AS days FROM stg.calendar GROUP BY 1) GROUP BY 1 ORDER BY 2 DESC LIMIT 3")
    out.append("\n\nDays per listing (top values): " + ", ".join(f"{r.days} days = {r.listings:,} listings" for r in days.itertuples()) +
               ".\n\n**Finding:** the calendar has **no price column** in this release and covers only the next 365 days, so price seasonality cannot be measured from it.")

    out.append("\n\n## 4. Null rates of key listing columns\n")
    cols = ["price", "bedrooms", "beds", "bathrooms_text", "review_scores_rating", "reviews_per_month", "license",
            "host_since", "host_response_rate", "host_total_listings_count", "instant_bookable", "estimated_revenue_l365d"]
    sel = ", ".join(f"ROUND(100.0 * COUNT(*) FILTER (WHERE {c} IS NULL) / COUNT(*), 1) AS {c}" for c in cols)
    nulls = q(f"SELECT {sel} FROM raw.listings").T.reset_index()
    nulls.columns = ["column", "pct_null"]
    out.append(md_table(nulls))
    out.append("\n\n**Findings:** host_since, host_response_rate, host_total_listings_count and instant_bookable are 100% empty in this scrape, so host type "
               "is derived from `calculated_host_listings_count`. Missing price (see section 5) marks listings that are not currently bookable.")

    out.append("\n\n## 5. Price parsing and outliers\n")
    out.append(md_table(q("""
        SELECT COUNT(*) AS listings,
               COUNT(*) FILTER (WHERE price IS NOT NULL) AS price_text_present,
               COUNT(*) FILTER (WHERE price_raw IS NOT NULL) AS parsed_ok,
               COUNT(*) FILTER (WHERE price IS NOT NULL AND price_raw IS NULL) AS parse_failed,
               COUNT(*) FILTER (WHERE price_raw IS NULL) AS no_price
        FROM (SELECT l.price, s.price_raw FROM raw.listings l JOIN stg.listings s ON s.listing_id = l.id)""")))
    pr = q("""SELECT ROUND(MIN(price_raw),1) AS min, ROUND(quantile_cont(price_raw, 0.01),1) AS p01, ROUND(median(price_raw),1) AS median,
              ROUND(quantile_cont(price_raw, 0.99),1) AS p99, ROUND(MAX(price_raw),1) AS max,
              COUNT(*) FILTER (WHERE price_raw < 10) AS below_10, COUNT(*) FILTER (WHERE price_raw > 1000) AS above_1000
              FROM stg.listings""")
    out.append("\n\n" + md_table(pr))
    out.append("\n\n**Rule:** prices outside 10-1,000 EUR/night are flagged `is_price_outlier` and excluded from price statistics (kept in the data, never deleted). "
               "Currency: the `$` in the source text is formatting; the price quote metadata says EUR.")

    out.append("\n\n## 6. Listing segments (what counts as 'the market')\n")
    out.append(md_table(q("""SELECT listing_segment, COUNT(*) AS listings, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
                             FROM mart.dim_listing GROUP BY 1 ORDER BY 2 DESC""")))
    out.append(f"\n\n**Benchmark population** (`is_benchmark`): priced, average minimum stay under 28 nights, price 10-1,000 EUR = "
               f"**{q('SELECT COUNT(*) FROM mart.dim_listing WHERE is_benchmark').iloc[0,0]:,} listings**. All price and revenue statistics use it unless stated.")

    out.append("\n\n## 7. Reviews date range\n")
    out.append(md_table(q("SELECT MIN(review_date) AS first_review, MAX(review_date) AS last_review, COUNT(*) AS reviews FROM raw.reviews").astype(str)))
    out.append("\n\n2026 is a partial year (ends 20 Sep). Reviews of listings that have left the platform are absent (survivorship): early years are understated.")

    out.append("\n\n## 8. Occupancy-formula reconciliation\n")
    rec = q("""SELECT COUNT(*) AS listings,
               ROUND(100.0 * AVG((ABS(est_nights_base - ia_est_occupancy_nights) <= 1)::INT), 1) AS pct_within_1_night_of_inside_airbnb,
               ROUND(100.0 * AVG((ABS(est_revenue_base - ia_est_revenue) <= 2)::INT) FILTER (WHERE ia_est_revenue > 0), 1) AS pct_revenue_within_2_eur
               FROM mart.fact_listing""")
    out.append(md_table(rec))
    out.append("\n\nOur 'base' scenario (review rate 0.50, average stay 6.3 nights, cap 255 nights) was reverse-engineered from the "
               "`estimated_occupancy_l365d` column and matches it for the share above. It is an **estimate**, not a measurement. "
               "Low/high scenarios are our own sensitivity bounds.")

    out.append("\n\n## 9. Sensitive fields\n")
    out.append(md_table(q("SELECT license_status, COUNT(*) AS listings FROM stg.listings GROUP BY 1 ORDER BY 2 DESC")))
    out.append("\n\nThe raw `license` text can contain private persons' names, so only the category above is carried into the model. "
               "Names, descriptions, host names/about, URLs, pictures and review comments are not loaded into any model table. "
               "`host_key` is an MD5 hash used only for counting and is excluded from every export.")
    return "\n".join(out) + "\n"


def main(db_path=DB_PATH):
    con = duckdb.connect(str(db_path), read_only=True)
    text = build_report(con)
    (DOCS_DIR / "DATA_QUALITY_REPORT.md").write_text(text, encoding="utf-8")
    print("wrote docs/DATA_QUALITY_REPORT.md")


if __name__ == "__main__":
    main()
