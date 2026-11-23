"""Run numbered SQL files against DuckDB.

Two kinds of files:
  * sql/00..03*.sql : multi-statement build scripts (reference, staging, dims, facts)
  * sql/1x_*.sql    : ONE SELECT each; the result is stored as analysis.<name> and exported to CSV.
"""
import re
import duckdb
from src.config import DB_PATH, SQL_DIR


def split_statements(sql: str):
    # strip -- line comments first (they may contain ';'), then split on ';'.
    # Our build files never put '--' or ';' inside string literals, so this is safe.
    sql = "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())
    return [s.strip() for s in sql.split(";") if s.strip()]


def run_build(con, prefix_max=3):
    for f in sorted(SQL_DIR.glob("0*.sql")):
        for stmt in split_statements(f.read_text(encoding="utf-8")):
            con.execute(stmt)
        print(f"built  {f.name}")


def run_analysis(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS analysis")
    names = []
    for f in sorted(SQL_DIR.glob("1*.sql")):
        name = re.sub(r"^\d+[a-z]?_", "", f.stem)
        con.execute(f"CREATE OR REPLACE TABLE analysis.{name} AS\n{f.read_text(encoding='utf-8').strip().rstrip(';')}")
        n = con.execute(f"SELECT count(*) FROM analysis.{name}").fetchone()[0]
        print(f"analysis.{name}: {n} rows  ({f.name})")
        names.append(name)
    return names


if __name__ == "__main__":
    c = duckdb.connect(str(DB_PATH))
    run_build(c)
    run_analysis(c)
