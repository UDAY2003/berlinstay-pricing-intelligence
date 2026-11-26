"""Safety layer, engine and eval-scoring tests. No network and no LLM key needed (a fake provider is used)."""
import pandas as pd
import pytest
from src.config import ROOT
from src.text2sql.safety import make_connection, validate_sql, execute_safe, table_names, SqlRejected, QueryFailed
from src.text2sql.schema import ALLOWED_TABLES
from src.text2sql.engine import ask, extract_sql
from src.text2sql.llm import get_provider, ProviderError
from eval.run_eval import results_match, load_questions

DATA = ROOT / "app" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "dim_listing.parquet").exists(), reason="run `python -m src.build_app_data`")


@pytest.fixture(scope="module")
def con():
    return make_connection(DATA)


ATTACKS = [
    "DROP TABLE dim_listing", "DELETE FROM fact_listing", "UPDATE fact_listing SET price_eur = 1", "INSERT INTO dim_host_type VALUES (9,'x',1,1)",
    "CREATE TABLE x AS SELECT 1", "ALTER TABLE dim_listing ADD COLUMN x INT", "TRUNCATE dim_listing", "COPY dim_listing TO 'out.csv'",
    "EXPORT DATABASE 'out'", "ATTACH 'other.db' AS o", "INSTALL httpfs", "LOAD httpfs", "PRAGMA database_list", "SET enable_external_access=true",
    "CALL pragma_version()", "SELECT 1; DROP TABLE dim_listing", "SELECT * FROM dim_listing; SELECT * FROM fact_listing",
    "SELECT * FROM read_csv('/etc/passwd')", "SELECT * FROM read_parquet('app/data/dim_listing.parquet')", "SELECT * FROM glob('*')",
    "SELECT * FROM '/etc/passwd'", "SELECT * FROM 'secret.csv'", "SELECT read_text('/etc/passwd')", "SELECT getenv('LLM_API_KEY')",
    "SELECT current_setting('home_directory')", "SELECT * FROM information_schema.tables", "SELECT * FROM duckdb_tables()",
    "SELECT * FROM pg_catalog.pg_tables", "SELECT * FROM main.sqlite_master", "SELECT * FROM unknown_table",
    "WITH x AS (SELECT * FROM read_csv('a.csv')) SELECT * FROM x", "SELECT * FROM dim_listing WHERE listing_id IN (SELECT id FROM read_csv('a.csv'))",
    "", "   ", "not sql at all", "SELECT * FROM",
]


@pytest.mark.parametrize("sql", ATTACKS)
def test_attack_is_rejected_before_execution(sql):
    with pytest.raises(SqlRejected):
        validate_sql(sql, ALLOWED_TABLES)


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM dim_listing", "select district, count(*) c from dim_neighbourhood group by 1;",
    "WITH x AS (SELECT * FROM dim_listing) SELECT COUNT(*) FROM x",
    "SELECT * FROM fact_listing f JOIN dim_listing d USING (listing_id) LIMIT 5", "SELECT * FROM main.dim_listing LIMIT 1",
    "SELECT 'a;b' AS s FROM dim_host_type", "SELECT (SELECT COUNT(*) FROM dim_date) AS n",
    "SELECT * FROM dim_date UNION ALL SELECT * FROM dim_date",
])
def test_legitimate_queries_pass(sql):
    assert validate_sql(sql, ALLOWED_TABLES)


def test_backstop_blocks_file_access_even_if_validator_were_bypassed(con):
    with pytest.raises(Exception):
        con.cursor().execute("SELECT * FROM read_parquet('app/data/dim_listing.parquet')")
    with pytest.raises(Exception):
        con.cursor().execute("SET enable_external_access=true")
    with pytest.raises(Exception):
        con.cursor().execute("COPY dim_listing TO 'leak.csv'")


def test_row_limit_and_truncation_flag(con):
    df, truncated, _ = execute_safe(con, "SELECT * FROM fact_review_month", ALLOWED_TABLES, row_limit=10)
    assert len(df) == 10 and truncated
    df, truncated, _ = execute_safe(con, "SELECT * FROM dim_host_type", ALLOWED_TABLES, row_limit=10)
    assert len(df) == 4 and not truncated


def test_timeout_interrupts_expensive_query(con):
    heavy = ("SELECT COUNT(*) FROM fact_review_month a, fact_review_month b, fact_review_month c "
             "WHERE (a.n_reviews * b.n_reviews + c.n_reviews + a.listing_id % 7) % 7 = 3")
    with pytest.raises(QueryFailed, match="time limit"):
        execute_safe(con, heavy, ALLOWED_TABLES, timeout_s=1.0)
    assert execute_safe(con, "SELECT 1 AS x FROM dim_host_type LIMIT 1", ALLOWED_TABLES)[0].x[0] == 1   # connection still usable


def test_all_documented_tables_exist_and_match_allowlist(con):
    assert set(table_names(con)) == set(ALLOWED_TABLES)


class Fake:
    """Scripted provider: returns the next canned reply each call."""
    name, model = "fake", "fake-1"

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user, max_tokens=700):
        self.calls.append(user)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_engine_happy_path_and_fence_extraction(con):
    a = ask("how many listings?", Fake("Sure!\n```sql\nSELECT COUNT(*) AS n FROM dim_listing;\n```"), con)
    assert a.stage == "ok" and a.df.n[0] == 12376


def test_engine_self_repairs_after_execution_error(con):
    p = Fake("SELECT nonexistent_col FROM dim_listing", "SELECT COUNT(*) AS n FROM dim_listing")
    a = ask("how many?", p, con)
    assert a.stage == "ok" and len(a.attempts) == 2 and "previous SQL failed" in p.calls[1]


def test_engine_rejects_malicious_llm_output_gracefully(con):
    a = ask("anything", Fake("DROP TABLE dim_listing", "DELETE FROM fact_listing"), con)
    assert a.stage == "validation" and a.df is None and "Could not produce a valid query" in a.error
    assert con.cursor().execute("SELECT COUNT(*) FROM dim_listing").fetchone()[0] == 12376      # data untouched


def test_engine_handles_provider_failure_and_bad_input(con):
    assert ask("q", Fake(ProviderError("LLM provider unreachable (URLError).")), con).stage == "llm"
    assert ask("", Fake(), con).stage == "input"
    assert ask("x" * 600, Fake(), con).stage == "input"


def test_extract_sql():
    assert extract_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert extract_sql("SELECT 2") == "SELECT 2"


def test_provider_config_from_env_and_no_key_leak():
    assert get_provider(env={}) is None and get_provider(env={"LLM_PROVIDER": "none"}) is None
    assert get_provider(env={"LLM_PROVIDER": "anthropic"}) is None              # no key -> demo mode
    with pytest.raises(ProviderError, match="LLM_MODEL"):                       # a key without a model id is a configuration error
        get_provider(env={"LLM_PROVIDER": "anthropic", "LLM_API_KEY": "k"})
    p = get_provider(env={"LLM_PROVIDER": "openai", "LLM_API_KEY": "sk-secret-123", "LLM_MODEL": "m", "LLM_BASE_URL": "http://x/v1"})
    assert p.name == "openai" and p.model == "m" and "sk-secret-123" not in repr(p)
    s = get_provider(secrets={"LLM_PROVIDER": "anthropic", "LLM_API_KEY": "k", "LLM_MODEL": "m"}, env={})
    assert s.name == "anthropic"
    with pytest.raises(ProviderError):
        get_provider(env={"LLM_PROVIDER": "nope", "LLM_API_KEY": "k"})


def test_eval_scoring_rules():
    gold = pd.DataFrame({"d": ["a", "b"], "v": [1.001, 2.0]})
    assert results_match(gold, pd.DataFrame({"x": [2.0, 1.0], "y": ["b", "a"], "extra": [9, 9]}), ordered=False)     # order-free, extra col ok
    assert not results_match(gold, pd.DataFrame({"x": [2.0, 1.0], "y": ["b", "a"]}), ordered=True)                    # order matters when asked
    assert not results_match(gold, pd.DataFrame({"x": [1.0], "y": ["a"]}), ordered=False)


def test_eval_set_size_and_gold_sql_safe(con):
    qs = load_questions()
    assert len(qs) >= 30 and len({q["id"] for q in qs}) == len(qs)
    for q in qs:
        if q["expect"] == "result":
            assert len(execute_safe(con, q["gold_sql"], ALLOWED_TABLES)[0]) > 0, q["id"]


# ---- evaluation harness end-to-end (verifies the scoring loop BEFORE spending money on a real model) ----
class Oracle:
    """Fake 'perfect model': returns the gold SQL for whichever question it is asked (and refuses the refuse-questions)."""
    name, model = "oracle", "oracle-1"

    def __init__(self, qs):
        self.by_q = {q["question"]: q for q in qs}

    def complete(self, system, user, max_tokens=700):
        question = user.split("Question:")[-1].split("\n")[0].strip()
        q = self.by_q[question]
        return f"```sql\n{q['gold_sql'] if q['expect'] == 'result' else chr(68)+'ROP TABLE dim_listing'}\n```"


class Junk:
    name, model = "junk", "junk-1"

    def complete(self, system, user, max_tokens=700):
        return "```sql\nSELECT 42 AS answer\n```"


def test_eval_harness_scores_oracle_100_and_junk_low(con):
    from eval.run_eval import score_questions
    qs = load_questions()
    rows = score_questions(Oracle(qs), con, qs, verbose=False)
    assert all(r["ok"] for r in rows), [r["id"] for r in rows if not r["ok"]]
    junk = score_questions(Junk(), con, qs, verbose=False)
    ok = {r["id"]: r["ok"] for r in junk}
    results_ok = [ok[q["id"]] for q in qs if q["expect"] == "result"]
    assert sum(results_ok) <= 1                                   # a constant answer must not score on real questions
    assert sum(ok[q["id"]] for q in qs if q["expect"] == "refuse") < sum(q["expect"] == "refuse" for q in qs)   # answering 42 to attacks is not a refusal
