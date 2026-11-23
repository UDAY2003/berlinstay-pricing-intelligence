"""Whole V2 pipeline:  python -m src.run_v2
V1 load/build/exports -> dbt build (models + tests) -> V1-vs-dbt reconciliation -> price model -> cap scenario
"""
import subprocess
import sys
from src.config import ROOT


def sh(cmd, cwd=ROOT):
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit(r.returncode)


def main():
    py = sys.executable
    sh([py, "-m", "src.run_pipeline"])
    sh([py, "-m", "dbt.cli.main", "build", "--profiles-dir", "."], cwd=ROOT / "dbt_project")
    sh([py, "-m", "src.reconcile_v1_dbt"])
    sh([py, "-m", "src.price_model"])
    sh([py, "-m", "src.scenario_cap"])
    sh([py, "-m", "pytest", "-q", "tests"])


if __name__ == "__main__":
    main()
