"""One command for the whole V1 pipeline:  python -m src.run_pipeline

load raw -> build staging/star schema -> run SQL analysis pack -> data-quality report -> exports
"""
import time
import duckdb
from src import load_data, dq_report, export
from src.config import DB_PATH
from src.run_sql import run_build, run_analysis


def main():
    t0 = time.time()
    load_data.load()
    con = duckdb.connect(str(DB_PATH))
    run_build(con)
    run_analysis(con)
    con.close()
    dq_report.main()
    export.export()
    print(f"pipeline finished in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
