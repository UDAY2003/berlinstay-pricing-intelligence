# Case study: BerlinStay Pricing Intelligence

## Problem
A host or small property manager in Berlin has to answer three questions with little reliable information: *what nightly price is sensible, what income is realistic, and how do seasonality and local rules change that?* Public listing data exists, but it contains traps: unpriced listings, mid-term stays mixed with tourist stays, estimated rather than observed occupancy, and regulation that is changing.

## Data
Inside Airbnb, Berlin, scraped 19 Sep 2026 (CC BY 4.0): 12,376 listings, a 4.5M-row forward calendar, 708,768 reviews, neighbourhood polygons. Profiling before modelling showed what the data can and cannot support:
- the calendar has **no price column** and only looks forward 365 days -> price seasonality cannot be measured;
- only **52%** of listings are priced short-stay listings (34% unpriced, 13.5% mid-term) -> a "benchmark population" had to be defined;
- host fields are empty in this release; the licence field contains personal names -> reduced to a category;
- `review_id` is not unique -> de-duplicating it moved 2026 review growth from 18.4% to 15.4%;
- the neighbourhood file ends with a blank row that produced a junk dimension member (found late, in V3, fixed at the source in V1 SQL and dbt, now covered by tests).

## Approach
1. **V1 Market analytics.** Raw -> staging -> star schema in DuckDB; an SQL analysis pack with CTEs and window functions (price by district and room type, supply concentration, multi-listing hosts, estimated occupancy and revenue, seasonality, demand trends); a generated data-quality report; an EDA notebook; Power BI build guide with DAX; business memo.
2. **V2 Pricing and scenarios.** The SQL was rebuilt in dbt-duckdb (staging -> intermediate -> marts, seeds, 44 tests) and reconciled against V1 table by table. A LightGBM price model was compared with a district x room-type median baseline using a **host-grouped** split and CV, a paired bootstrap, SHAP and segment error analysis. A revenue what-if calculator and a 90-night-cap **scenario** (assumption-driven, with the regulation described only from the official source and flagged "verify") were added.
3. **V3 AI pricing assistant.** A Streamlit app (market explorer, price estimator, scenario simulator) and an "Ask the data" assistant: an LLM writes SQL, but nothing it writes is trusted. The SQL is parsed by DuckDB (single SELECT only), checked against a table allow-list, run on a locked in-memory database with no file access, with a row limit and a timeout. The provider is configurable by environment variables.

## Results
| Question | Result (estimates marked) |
|---|---|
| Typical prices | median 181 EUR/night entire home (middle half 135-256), 91 EUR private room; Mitte 205, Reinickendorf 115 (entire homes) |
| Realistic income (estimate, gross) | entire home median 16.8k / 26.0k / 29.1k EUR per year (low / base / high); the mean is about 31% above the median; top 10% of listings earn about a third of revenue |
| Seasonality (review proxy) | strongest Sep (1.25), Jul, Jun, Oct; weakest Jan (0.63) and Feb (0.70); events: Festival of Lights, Christmas/New Year, Marathon weekend, Easter show higher unavailability, Berlinale/ITB/Pride none (directional only) |
| Pricing model | held-out MAE 53.6 vs 66.7 EUR for the baseline (95% CI of the difference -15.8 to -10.5); R2 on log price 0.53 |
| 90-night cap scenario | at an assumed 20% share of single-host entire homes, about 2.6% of estimated market revenue affected (1.1% with 50% re-booking); 0.6-3.9% for 5-30% shares |
| Migration | 18 of 19 tables identical to V1; one NULL-logic bug found by a dbt test |
| Assistant safety | 36/36 adversarial SQL strings rejected before execution; backstop, timeout and row-limit verified |

## Limitations
- Occupancy and revenue are **estimates** from a review-rate model (reconciled to Inside Airbnb's own estimate, but both rest on assumed review and stay rates); listings with no reviews count as zero nights; gross, before fees, taxes and costs.
- The calendar cannot separate booked from blocked nights, has no prices, and mixes seasonality with booking lead time.
- The model predicts **asking** prices of comparable listings; it is not better for private rooms or the 150-250 EUR band, under-predicts expensive listings, and its 80% interval covers 72%.
- The cap scenario cannot identify second homes; the share is an assumption. Regulation details (scope, dates, exceptions) must be verified with official Berlin sources; this is not legal advice.
- One snapshot; anonymised locations (~150 m); reviews of delisted listings are missing.
- **The LLM assistant's accuracy has not been measured yet** (no API key was available); the evaluation harness and a 42-question set are ready (`docs/EVAL.md`).

## What I would do next
1. Run the evaluation with a real provider, read every failure, and fix the schema prompt/few-shot examples; report accuracy by category.
2. Add calendar prices from a later scrape (or a second source) to measure seasonal and event price premiums instead of only demand timing.
3. Calibrate the prediction interval (conformal prediction) so the nominal 80% is honest, and test richer features (amenity categories, text embeddings of titles) against the same baseline.
4. Replace the review-rate occupancy assumption with a calibrated one if booking data from a partner host group becomes available.
5. Monitoring: scheduled refresh when Inside Airbnb publishes a new scrape; dbt tests as the data contract; cost and abuse limits on the public assistant.
