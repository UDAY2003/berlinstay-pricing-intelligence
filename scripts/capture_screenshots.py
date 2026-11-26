"""Capture the four app screenshots for the README (Windows, needs Microsoft Edge) and trim empty space.

  1. start the app:   streamlit run app/streamlit_app.py --server.port 8501
  2. run:             python scripts/capture_screenshots.py
Each tab is opened through its ?tab= deep link. A long virtual-time budget lets Streamlit finish rendering
(an earlier capture taken too early was blank; the script refuses to save an image that is mostly white).
"""
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
TABS = {"Market Explorer": "app_market_explorer", "Price Estimator": "app_price_estimator",
        "Scenario Simulator": "app_scenario_simulator", "Ask the data": "app_ask_the_data"}


def main(port=8501, width=1400, height=1900):
    for tab, name in TABS.items():
        out = ROOT / "docs" / "img" / f"{name}.png"
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}", "--virtual-time-budget=90000",
                        f"--screenshot={out}", f"http://localhost:{port}/?tab={quote(tab)}"], check=True, capture_output=True)
        img = Image.open(out).convert("RGB")
        a = np.asarray(img)
        rows = np.where((a < 245).any(axis=(1, 2)))[0]
        if len(rows) < 200:
            sys.exit(f"{name}: page looks blank, not saved - increase the time budget or check the app")
        img.crop((0, 0, width, min(height, rows.max() + 40))).save(out)
        print(f"{name}.png  {img.size} -> kept {rows.max() + 40}px of content")


if __name__ == "__main__":
    main()
