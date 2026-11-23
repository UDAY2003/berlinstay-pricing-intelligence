# Text-to-SQL evaluation (V3)

## Set-up
- **Questions:** `eval/questions.jsonl`, **42 questions**: 35 with gold SQL (count 7, price 8, supply 4, revenue 5, reviews 5, calendar 3, pricing gap 2, licence 1) and 7 that must be *refused* (3 unanswerable from the data, 4 adversarial: DROP TABLE, read a system file, DELETE, schema listing).
- **Metric:** *execution accuracy*. The result of the generated SQL must equal the result of the gold SQL (values compared, column names ignored, floats rounded to 2 decimals, extra columns tolerated, row order checked only when the question asks for an order). Refusal questions pass if no data is returned (validation rejects the SQL, or the explicit "cannot be answered" message).
- **Run:** `python -m eval.run_eval --provider env` (needs `LLM_PROVIDER`, `LLM_API_KEY`, optional `LLM_MODEL`). It writes `eval/results_<model>.json` and `docs/EVAL_REPORT.md` with accuracy by category, every failure (generated vs gold SQL) and a diagnosis placeholder per failure.
- **Gold validation without an LLM:** `python -m eval.run_eval --validate-gold` -> all 35 gold queries pass the safety layer and return rows (verified).

## Status: LLM accuracy NOT yet measured
No LLM API key was available while building V3, so **no accuracy number exists yet** and none is claimed. What has been verified without an LLM:

| Check | Result |
|---|---|
| Gold SQL passes safety layer and returns rows | 35/35 |
| Adversarial SQL rejected before execution (`tests/test_text2sql.py`: DDL/DML, multi-statement, file reads, table functions, system catalogs, env/settings functions, malformed input) | 36/36 |
| Legitimate queries (CTE, joins, set operations, semicolons inside strings, `main.` prefix) accepted | 8/8 |
| Backstop: even if validation were bypassed, file access, COPY and `SET enable_external_access` fail on the locked connection | verified |
| Row limit and truncation flag; 1 s timeout interrupts a runaway query and the connection stays usable | verified |
| Engine with a scripted fake provider: fenced-SQL extraction, one self-repair after a SQL error, graceful handling of malicious output, provider outage, empty/oversized input | verified |
| Scoring function (order-free match, extra columns, order-sensitive match, row-count mismatch) | verified |

## Safety layer: failure cases found while building, and fixes
1. **Parsing by regex is unsafe** -> use DuckDB's own parser (`json_serialize_sql`): it refuses anything that is not a single SELECT and gives an AST, so table names are read from the parse tree, not from text.
2. **A file path can masquerade as a table** (`SELECT * FROM '/etc/passwd'`, replacement scans) -> every `BASE_TABLE` must be on the allow-list or be a CTE defined in the query; any `TABLE_FUNCTION` (`read_csv`, `glob`, `duckdb_tables()`) is rejected.
3. **Scalar functions can reach files or the environment** (`read_text`, `getenv`, `current_setting`) -> function deny-list by prefix.
4. **System catalogs leak structure** (`information_schema`, `pg_catalog`) -> schema-qualified tables other than `main` are rejected.
5. **Validators can have bugs** -> second layer: in-memory database loaded from parquet, then `enable_external_access=false` and `lock_configuration=true`.
6. **Runaway queries** -> the query is wrapped in `LIMIT n+1` (to flag truncation) and a timer interrupts the cursor after 8 s. A first version of the timeout test used a query DuckDB optimised away from its statistics; the test now uses a genuinely expensive cross join.
7. **Prompt injection** -> the question is passed as data; whatever the model returns must still pass the validator, so a successful injection can at most produce a harmless allowed SELECT. Data values are never sent back to the model (only the DB error message on the repair step).

## Expected LLM failure modes (hypotheses to test, not results)
- forgetting the `is_benchmark` filter, or using AVG instead of MEDIAN for "typical";
- wrong join keys (`neighbourhood_key` vs `listing_id`) or double-counting by joining two facts;
- confusing "last 12 months" columns with calendar years; partial 2026 data;
- answering questions the data cannot answer (December prices, host names, second homes) instead of refusing.
After running the evaluation, fill in each failure's diagnosis in `docs/EVAL_REPORT.md` and note which prompt/schema change fixed it (the schema text lives in `src/text2sql/schema.py`).
