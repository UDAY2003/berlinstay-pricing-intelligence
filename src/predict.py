"""Price estimation for ONE listing from user inputs (used by the Streamlit app). Light dependencies: pandas, numpy, lightgbm via joblib.

build_row() reproduces the training-time feature engineering of src/features.py (same columns, same categories, same formulas).
The model is a LightGBM trained on log(price); outputs are exponentiated. q10/q90 are quantile models: an APPROXIMATE range
(empirical coverage on held-out hosts was 72% for the nominal 80%).
"""
import joblib
import numpy as np
import pandas as pd

CENTER = (52.5208, 13.4095)


def haversine_km(lat, lon, lat0=CENTER[0], lon0=CENTER[1]):
    p = np.pi / 180
    a = 0.5 - np.cos((lat - lat0) * p) / 2 + np.cos(lat0 * p) * np.cos(lat * p) * (1 - np.cos((lon - lon0) * p)) / 2
    return 12742 * np.arcsin(np.sqrt(a))


def load_bundle(path):
    return joblib.load(path)


def capacity_band(n):
    return "1-2" if n <= 2 else "3-4" if n <= 4 else "5-6" if n <= 6 else "7+"


def build_row(bundle, *, room_type, property_type_grp, district, neighbourhood, latitude, longitude, accommodates, bedrooms, beds, bathrooms,
              has_shared_bath=False, amenities_count=30, is_superhost=False, host_listings_count=1, minimum_nights_avg=2):
    row = dict(room_type=room_type, property_type_grp=property_type_grp, district=district, neighbourhood=neighbourhood,
               accommodates=accommodates, bedrooms=bedrooms, beds=beds, bathrooms=bathrooms, has_shared_bath=int(has_shared_bath),
               amenities_count=amenities_count, is_superhost=int(is_superhost), host_listings_count=host_listings_count,
               latitude=latitude, longitude=longitude, dist_center_km=float(haversine_km(latitude, longitude)),
               minimum_nights_avg=minimum_nights_avg, is_entire_home=int(room_type == "Entire home/apt"),
               people_per_bedroom=accommodates / max(bedrooms, 1))
    df = pd.DataFrame([row])
    for c, cats in bundle["categories"].items():
        if row[c] not in cats:
            raise ValueError(f"unknown {c}: {row[c]!r}")
        df[c] = pd.Categorical(df[c], categories=cats)
    return df[bundle["features"]]


def predict(bundle, **inputs) -> dict:
    X = build_row(bundle, **inputs)
    pred = float(np.exp(bundle["model"].predict(X))[0])
    lo, hi = float(np.exp(bundle["q10"].predict(X))[0]), float(np.exp(bundle["q90"].predict(X))[0])
    lo, hi = min(lo, pred), max(hi, pred)                      # quantile models can cross the point estimate; keep the range coherent
    base = float(bundle["baseline"].predict(pd.DataFrame({"district": [inputs["district"]], "room_type": [inputs["room_type"]]}))[0])
    return {"price": round(pred, 1), "low": round(lo, 1), "high": round(hi, 1), "baseline": round(base, 1)}
