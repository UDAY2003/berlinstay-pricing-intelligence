# CV / LinkedIn drafts (edit to the roles you apply for; only keep claims you can explain)

**Project line:** BerlinStay Pricing Intelligence - end-to-end analytics project on Berlin short-term rentals (Inside Airbnb, CC BY 4.0): DuckDB + SQL + dbt, Power BI, LightGBM pricing model, scenario analysis, Streamlit app with a guarded text-to-SQL assistant.

CV bullets (pick 3-4):
- Built a DuckDB star schema (12k listings, 4.5M calendar rows, 709k reviews) with a data-quality report; found and fixed repeated review IDs that overstated 2026 demand growth by 3 percentage points.
- Migrated 19 SQL models to dbt-duckdb (44 tests incl. relationships and business rules) and proved equivalence with set-difference reconciliation; a dbt test exposed a NULL-logic bug in the original SQL.
- Trained a LightGBM nightly-price model with host-grouped cross-validation: MAE 53.6 EUR vs 66.7 EUR for a district x room-type median baseline (95% CI of the difference -15.8 to -10.5), and reported where it does not help (private rooms, mid-price band; interval under-coverage 72% vs 80%).
- Modelled a 90-night-cap regulation scenario with explicit assumptions and sensitivity ranges (about 2.6% of estimated market revenue at a 20% assumed share), clearly separated from legal facts.
- Shipped a Streamlit app (market explorer, price estimator, scenario simulator) and a text-to-SQL assistant with defence-in-depth safety (parser-validated single SELECT, table allow-list, locked read-only DuckDB, row/time limits) covered by 36 adversarial tests and a 42-question evaluation harness.

LinkedIn post / About snippet (about 60 words):
"I analysed Berlin's short-term-rental market end to end: DuckDB/SQL/dbt pipeline, Power BI dashboard guide, a pricing model that beats a median baseline on unseen hosts (and an honest list of where it doesn't), a regulation scenario, and a Streamlit app with a safe natural-language-to-SQL assistant. Data: Inside Airbnb. Repo and live app linked below."

Interview one-liners: "I report estimates as estimates"; "I compare every model to a simple baseline with a grouped split"; "the LLM never executes anything: SQL is parsed, allow-listed and run on a locked, read-only database".
