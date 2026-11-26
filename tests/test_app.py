"""Headless smoke test of the Streamlit app (all four tabs render, demo mode works, no exceptions)."""
import pytest
from src.config import ROOT

pytestmark = pytest.mark.skipif(not (ROOT / "app" / "data" / "dim_listing.parquet").exists(), reason="run `python -m src.build_app_data`")


def test_app_renders_and_demo_query_runs(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180).run()
    assert not at.exception
    assert len(at.tabs) == 4 and len(at.metric) >= 10
    assert at.code and at.code[-1].value.lower().startswith("select"), "demo mode must show a validated example result immediately"
    assert len(at.table) >= 1
    first = at.code[-1].value
    sel = [s for s in at.selectbox if s.label.startswith("Example question")][0]
    sel.select_index(0).run()                         # pick another example: a different query runs, no button needed
    assert not at.exception and at.code[-1].value != first


def test_safety_playground_blocks_attacks_and_allows_safe_sql(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180).run()
    assert any("BLOCKED before execution" in e.value for e in at.error)          # default example is an attack
    pick = [s for s in at.selectbox if s.label == "Example"][0]
    pick.select("A harmless allowed query").run()
    assert any(str(x.value).startswith("ALLOWED") for x in at.success)
    pick.select("Read a file from disk").run()
    assert any("not allowed" in e.value.lower() for e in at.error)
