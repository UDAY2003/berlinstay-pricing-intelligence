#!/usr/bin/env bash
# One command that proves the project is healthy:  bash scripts/check.sh
# Run from the repo root with the venv activated (source venv/Scripts/activate).
set -e
echo "== 1/5 rebuild everything (V1 pipeline, dbt build + tests, reconciliation, model, scenario, app data)"
python -m src.run_v2
python -m src.build_app_data
echo "== 2/5 Power BI reference values"
python -m src.powerbi_expected > /dev/null
echo "== 3/5 evaluation gold SQL"
python -m eval.run_eval --validate-gold
echo "== 4/5 full test suite"
python -m pytest -q tests
echo "== 5/5 working tree"
git status --short
echo "ALL CHECKS PASSED"
