# reports/ - committed results

Everything here is generated (by `python -m src.run_v2`) and committed so the results can be read without running anything.

| File | What it is |
|---|---|
| `analysis_tables/*.csv` | answers of the 11 SQL analysis queries (price by district and room type, supply concentration, multi-listing hosts, estimated occupancy and revenue, seasonal index, monthly review series, forward availability by week and event, review demand trends, licence field status, neighbourhood summary for the map) |
| `price_model_metrics.json` | cross-validation and held-out test metrics, bootstrap comparison, interval coverage, best parameters |
| `price_model_segment_errors.csv` | error of baseline vs model by room type, district, capacity, price band |
| `price_model_shap_importance.csv` | mean absolute SHAP value per feature |
| `scenario_cap_sensitivity.csv`, `scenario_cap_by_district_base_20pct.csv` | 90-night-cap scenario results (an assumption-driven scenario, not a forecast) |

Narrative versions: `docs/PRICE_MODEL_REPORT.md`, `docs/REGULATION_SCENARIO.md`, `docs/DATA_QUALITY_REPORT.md`, `docs/V1_V2_RECONCILIATION.md`, `docs/POWERBI_EXPECTED_VALUES.md`. Charts: `docs/img/`.
