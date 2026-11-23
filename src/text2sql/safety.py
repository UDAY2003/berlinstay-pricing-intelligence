"""Safety layer for LLM-generated SQL. Defence in depth - every layer must pass:

  1. VALIDATE (before execution): DuckDB's own parser must accept exactly ONE statement and it must be a SELECT
     (json_serialize_sql only serialises SELECTs; DDL/DML/PRAGMA/ATTACH/COPY/SET/INSTALL are rejected by the parser).
  2. ALLOW-LIST: every table in the parsed AST must be an allowed table or a CTE defined in the same query;
     table functions (read_csv, read_parquet, glob, ...) and file-path 'tables' are rejected.
  3. FUNCTION DENY-LIST: scalar functions that touch files, environment or settings are rejected.
  4. EXECUTE with limits: ROW LIMIT (query is wrapped, extra row detects truncation) and TIMEOUT (interrupt after N seconds).
  5. CONNECTION HARDENING (see make_connection): in-memory database loaded from parquet, then external access disabled
     and the configuration locked, so even a validator bug cannot read files, write files or change settings.
Errors are raised as SqlRejected / QueryFailed with messages that are safe to show to the user.
"""
import json
import threading
from pathlib import Path
import duckdb
import pandas as pd

MAX_SQL_CHARS = 4000
DENY_FUNCTIONS = ("read_", "glob", "getenv", "current_setting", "pragma", "duckdb_", "sniff", "parquet_", "load_", "http", "write_", "copy", "query")
_PARSER = duckdb.connect(":memory:")      # throwaway connection, no data: used only to parse SQL


class SqlRejected(Exception):
    """The SQL did not pass validation (never executed)."""


class QueryFailed(Exception):
    """The SQL was valid but failed or exceeded a limit at execution time."""


def _walk(node, cb):
    if isinstance(node, dict):
        cb(node)
        for v in node.values():
            _walk(v, cb)
    elif isinstance(node, list):
        for v in node:
            _walk(v, cb)


def validate_sql(sql: str, allowed_tables) -> str:
    """Return the cleaned single SELECT statement or raise SqlRejected."""
    if not isinstance(sql, str) or not sql.strip():
        raise SqlRejected("Empty query.")
    sql = sql.strip().rstrip(";").strip()
    if len(sql) > MAX_SQL_CHARS:
        raise SqlRejected("Query too long.")
    allowed = {t.lower() for t in allowed_tables}
    try:
        res = json.loads(_PARSER.execute("SELECT json_serialize_sql(?)", [sql]).fetchone()[0])
    except Exception as e:                                          # parser crash -> reject, do not execute
        raise SqlRejected(f"Could not parse query: {str(e)[:120]}")
    if res.get("error"):
        msg = res.get("error_message", "")
        if "Only SELECT" in msg:
            raise SqlRejected("Only a single read-only SELECT query is allowed.")
        raise SqlRejected(f"Query is not valid SQL: {msg[:160]}")
    stmts = res.get("statements", [])
    if len(stmts) != 1:
        raise SqlRejected("Exactly one statement is allowed.")

    ctes, problems = set(), []

    def collect_ctes(n):
        if "cte_map" in n and isinstance(n["cte_map"], dict):
            for entry in n["cte_map"].get("map", []):
                ctes.add(str(entry.get("key", "")).lower())

    _walk(stmts[0], collect_ctes)

    def check(n):
        t = n.get("type")
        if t == "BASE_TABLE":
            name = str(n.get("table_name", "")).lower()
            if n.get("catalog_name") or (n.get("schema_name") not in ("", None, "main")):
                problems.append(f"schema/catalog-qualified table '{n.get('schema_name')}.{name}'")
            elif name not in allowed and name not in ctes:
                problems.append(f"table '{name}' is not allowed")
        elif t == "TABLE_FUNCTION":
            problems.append("table functions are not allowed")
        elif t == "FUNCTION":
            fn = str(n.get("function_name", "")).lower()
            if any(fn.startswith(p) for p in DENY_FUNCTIONS):
                problems.append(f"function '{fn}' is not allowed")

    _walk(stmts[0], check)
    if problems:
        raise SqlRejected("Not allowed: " + "; ".join(sorted(set(problems))) + ".")
    return sql


def make_connection(data_dir: Path, memory_limit: str = "512MB") -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB loaded from the parquet sample, then locked down (no file access, config locked)."""
    con = duckdb.connect(":memory:")
    for f in sorted(Path(data_dir).glob("*.parquet")):
        con.execute(f"CREATE TABLE {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute("SET threads=2")
    con.execute("SET enable_external_access=false")
    con.execute("SET lock_configuration=true")
    return con


def table_names(con) -> list:
    return [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()]


def execute_safe(con, sql: str, allowed_tables, row_limit: int = 200, timeout_s: float = 8.0):
    """Validate then execute with a row limit and timeout. Returns (DataFrame, truncated: bool, cleaned_sql)."""
    clean = validate_sql(sql, allowed_tables)
    cur = con.cursor()
    timer = threading.Timer(timeout_s, cur.interrupt)
    timer.start()
    try:
        df = cur.execute(f"SELECT * FROM ({clean}) AS _q LIMIT {int(row_limit) + 1}").df()
    except duckdb.InterruptException:
        raise QueryFailed(f"Query exceeded the {timeout_s:.0f}s time limit.")
    except Exception as e:
        raise QueryFailed(str(e).splitlines()[0][:300])
    finally:
        timer.cancel()
        cur.close()
    truncated = len(df) > row_limit
    return df.head(row_limit), truncated, clean
