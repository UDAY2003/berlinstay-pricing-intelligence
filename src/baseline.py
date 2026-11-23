"""Median-by-segment baseline. Kept in its own light module so the saved model bundle can be unpickled
by the Streamlit app without importing shap/matplotlib (src.price_model)."""
import numpy as np
import pandas as pd


class MedianBaseline:
    """Median price of a segment; falls back to coarser segments when a segment has < min_n listings."""

    def __init__(self, keys, min_n=5):
        self.keys, self.min_n = list(keys), min_n

    def fit(self, X, y):
        d = X[self.keys].astype(str).assign(y=np.asarray(y))
        self.global_ = d.y.median()
        self.tables_ = []
        for k in range(len(self.keys), 0, -1):          # finest -> coarsest
            keys = self.keys[:k]
            g = d.groupby(keys, observed=True).y.agg(["median", "size"])
            self.tables_.append((keys, g[g["size"] >= self.min_n]["median"]))
        return self

    def predict(self, X):
        d = X[self.keys].astype(str)
        out = pd.Series(np.nan, index=d.index)
        for keys, tab in self.tables_:
            idx = pd.MultiIndex.from_frame(d[keys]) if len(keys) > 1 else pd.Index(d[keys[0]])
            vals = pd.Series(tab.reindex(idx).values, index=d.index)
            out = out.fillna(vals)
        return out.fillna(self.global_).values
