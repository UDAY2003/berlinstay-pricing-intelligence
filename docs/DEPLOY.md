# Deploy the app on Streamlit Community Cloud

The app (`app/streamlit_app.py`) runs from a **2.3 MB committed data sample** (`app/data/*.parquet`, opaque listing ids, no host or text fields) and a 1.8 MB model (`app/model/price_model.joblib`). Raw Inside Airbnb files and the DuckDB database are **not** committed and not needed.

## 0. Run it locally first
```powershell
source venv/Scripts/activate
streamlit run app/streamlit_app.py
```
Opens http://localhost:8501. Without an LLM key the "Ask the data" tab runs in demo mode (pre-written queries through the same safety layer).

## 1. Prepare the repository
1. Refresh the sample if data or model changed: `python -m src.run_v2 && python -m src.build_app_data`
2. Check nothing sensitive is tracked: `git ls-files | grep -E "raw|duckdb|secrets.toml$"` must print nothing (`secrets.toml.example` is fine).
3. Push to GitHub (done for this project; public is simplest for the free tier). `data/` (raw data, database) is git-ignored by design; `app/data/` is committed.

## 2. Create the app
The repository is already on GitHub: https://github.com/UDAY2003/berlinstay-pricing-intelligence. A pre-filled deploy link (you still sign in to Streamlit with GitHub and confirm; if the form opens empty, enter the values below by hand):
https://share.streamlit.io/deploy?repository=UDAY2003/berlinstay-pricing-intelligence&branch=main&mainModule=app/streamlit_app.py

1. Go to https://share.streamlit.io, sign in with GitHub, **Create app**, pick the repository and branch `main`.
2. **Main file path:** `app/streamlit_app.py`
3. **Advanced settings:** choose a Python version (the project was developed on 3.13; 3.12 also works with the pinned packages if 3.13 is unavailable) and paste secrets (next step).
4. Dependencies come from `app/requirements.txt` (the minimal list, located next to the entry file). The root `requirements.txt` also contains dbt and is only for local development. If the deploy log shows the root file being used, check the file location setting and that `app/requirements.txt` is committed.

## 3. Secrets (LLM for "Ask the data")
In **Settings > Secrets** paste (see `app/.streamlit/secrets.toml.example`):
```toml
LLM_PROVIDER = "anthropic"        # or "openai" (any OpenAI-compatible endpoint) or "none"
LLM_API_KEY  = "your-key"
LLM_MODEL = "your-model-id"            # required when a provider is set
# LLM_BASE_URL = ""
# LLM_MAX_QUESTIONS_PER_SESSION = 15
```
Never commit a key. The key is read at runtime from secrets or environment variables, never printed or logged. Without secrets the tab stays in demo mode. Set a spending limit at your LLM provider: the per-session question cap (default 15) limits cost but is not a security control.

## 4. After deploying
This project's live app: https://uday2003-berlinstay-pricing-intelligenc-appstreamlit-app-r7kuvt.streamlit.app/ (free apps sleep after inactivity, so the first load can take a few seconds; every push to `main` redeploys it automatically).

- Open the app, check each tab, and in "Ask the data" try one example and one malicious input such as `DROP TABLE dim_listing`.
- Put the app URL in `README.md` (replace the live-link placeholder) and add 2-3 screenshots to `docs/img/`.
- Free apps sleep after inactivity; the first load afterwards takes a few seconds.

## 5. What leaves the machine
Only the question text and the static table schema go to the LLM provider. No data rows, no secrets. Check your provider's data-use terms before putting a key into a public app.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: src` | the app adds the repo root to `sys.path`; make sure `src/` is committed and the main file path is `app/streamlit_app.py` |
| model fails to load (`MedianBaseline`) | commit `src/baseline.py` and keep `lightgbm`/`scikit-learn` versions as pinned (a pickled model is version-sensitive) |
| empty charts | `app/data/*.parquet` not committed (check `.gitignore` allows `app/data/`) |
| "Ask the data" always demo | secrets missing or `LLM_PROVIDER = "none"` |
