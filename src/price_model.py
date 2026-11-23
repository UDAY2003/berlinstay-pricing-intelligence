"""V2 price model: honest comparison of a median baseline against gradient boosting.

Protocol (all choices are made on TRAIN only; TEST is touched once):
  * split by HOST (GroupShuffleSplit): listings of one host never sit on both sides (hosts clone listings/prices)
  * target = log(price); metrics are reported in EUR (MAE) and percent (MAPE, median APE)
  * baselines: district x room_type median (the required baseline) and district x room_type x capacity median (stronger)
  * LightGBM tuned with a small random search under GroupKFold CV on train, same folds for every model
  * paired bootstrap of the test-set MAE difference decides whether the model really beats the baseline
Run:  python -m src.price_model
"""
import json
import warnings
import joblib
import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from src.config import ROOT, DOCS_DIR
from src.baseline import MedianBaseline
from src.features import load_model_frame, LISTING_FEATURES, ALL_FEATURES

warnings.filterwarnings("ignore")
SEED = 42
MODEL_DIR = ROOT / "models"
IMG = DOCS_DIR / "img"


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    ape = np.abs(p - y) / y
    ly, lp = np.log(y), np.log(p)
    return {"MAE": float(np.mean(np.abs(p - y))), "MAPE": float(100 * ape.mean()), "MdAPE": float(100 * np.median(ape)),
            "R2_log": float(1 - ((ly - lp) ** 2).sum() / ((ly - ly.mean()) ** 2).sum()), "bias": float(np.mean(p - y))}


def lgb_model(params, cat_cols):
    return lgb.LGBMRegressor(objective="regression", random_state=SEED, verbose=-1, n_jobs=4,
                             cat_smooth=20, min_data_per_group=20, cat_l2=10, **params)


def cv_scores(make, X, y, groups, folds):
    res = []
    for tr, va in folds:
        m = make().fit(X.iloc[tr], np.log(y.iloc[tr]))
        res.append(metrics(y.iloc[va], np.exp(m.predict(X.iloc[va]))))
    return pd.DataFrame(res).mean().to_dict()


def cv_baseline(keys, X, y, folds):
    res = []
    for tr, va in folds:
        b = MedianBaseline(keys).fit(X.iloc[tr], y.iloc[tr])
        res.append(metrics(y.iloc[va], b.predict(X.iloc[va])))
    return pd.DataFrame(res).mean().to_dict()


def main():
    df = load_model_frame()
    y = df.price_eur
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr_idx, te_idx = next(gss.split(df, y, groups=df.host_key))
    train, test = df.iloc[tr_idx].reset_index(drop=True), df.iloc[te_idx].reset_index(drop=True)
    ytr, yte = train.price_eur, test.price_eur
    print(f"train {len(train)} | test {len(test)} | hosts overlap: {len(set(train.host_key) & set(test.host_key))}")

    folds = list(GroupKFold(n_splits=5).split(train, ytr, groups=train.host_key))
    out = {"n_train": len(train), "n_test": len(test), "cv": {}, "test": {}}

    # ---- baselines ----------------------------------------------------------------------------
    BASE_KEYS = ["district", "room_type"]
    BASE2_KEYS = ["district", "room_type", "capacity_band"]
    out["cv"]["baseline_district_room"] = cv_baseline(BASE_KEYS, train, ytr, folds)
    out["cv"]["baseline_plus_capacity"] = cv_baseline(BASE2_KEYS, train, ytr, folds)

    # ---- LightGBM: small random search on CV (listing-only features) --------------------------
    rng = np.random.default_rng(SEED)
    space = dict(num_leaves=[7, 15, 31, 63], min_child_samples=[10, 20, 40], learning_rate=[0.03, 0.05, 0.08],
                 n_estimators=[200, 400, 700], colsample_bytree=[0.6, 0.8, 1.0], subsample=[0.7, 0.9], reg_lambda=[0, 1, 10])
    trials = []
    for i in range(14):
        p = {k: (v[rng.integers(len(v))]) for k, v in space.items()}
        p["subsample_freq"] = 1
        sc = cv_scores(lambda: lgb_model(p, None), train[LISTING_FEATURES], ytr, train.host_key, folds)
        trials.append((sc["MAE"], p, sc))
        print(f"  trial {i:2d}  CV MAE {sc['MAE']:.2f}  {p}")
    trials.sort(key=lambda t: t[0])
    best_params = trials[0][1]
    out["best_params"] = best_params
    out["cv"]["lightgbm_listing_features"] = trials[0][2]
    out["cv"]["lightgbm_with_performance"] = cv_scores(lambda: lgb_model(best_params, None), train[ALL_FEATURES], ytr, train.host_key, folds)

    # ---- final fit on TRAIN, evaluate on TEST once ---------------------------------------------
    b1 = MedianBaseline(BASE_KEYS).fit(train, ytr)
    b2 = MedianBaseline(BASE2_KEYS).fit(train, ytr)
    m = lgb_model(best_params, None).fit(train[LISTING_FEATURES], np.log(ytr))
    m_perf = lgb_model(best_params, None).fit(train[ALL_FEATURES], np.log(ytr))
    preds = {"baseline_district_room": b1.predict(test), "baseline_plus_capacity": b2.predict(test),
             "lightgbm_listing_features": np.exp(m.predict(test[LISTING_FEATURES])),
             "lightgbm_with_performance": np.exp(m_perf.predict(test[ALL_FEATURES]))}
    for k, p in preds.items():
        out["test"][k] = metrics(yte, p)

    # paired bootstrap on test: is the model's MAE lower than the baseline's?
    ae = {k: np.abs(p - yte.values) for k, p in preds.items()}
    boot = {}
    for a, b in [("lightgbm_listing_features", "baseline_district_room"), ("lightgbm_listing_features", "baseline_plus_capacity")]:
        d = ae[a] - ae[b]
        bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)])
        boot[f"{a}_minus_{b}"] = {"mean_diff_MAE": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                  "p_model_better": float((bs < 0).mean())}
    out["bootstrap"] = boot

    # ---- prediction interval via quantile models ------------------------------------------------
    q = {}
    for a in (0.1, 0.9):
        qm = lgb.LGBMRegressor(objective="quantile", alpha=a, random_state=SEED, verbose=-1, n_jobs=4, cat_smooth=20,
                               min_data_per_group=20, cat_l2=10, **best_params).fit(train[LISTING_FEATURES], np.log(ytr))
        q[a] = np.exp(qm.predict(test[LISTING_FEATURES]))
    cover = float(((yte.values >= q[0.1]) & (yte.values <= q[0.9])).mean())
    out["interval_80pct"] = {"nominal": 0.8, "test_coverage": cover, "median_width_eur": float(np.median(q[0.9] - q[0.1]))}

    # ---- segment error analysis ----------------------------------------------------------------
    t = test.assign(y=yte, base=preds["baseline_district_room"], gbm=preds["lightgbm_listing_features"])
    t["price_band"] = pd.cut(t.y, [0, 80, 150, 250, 1001], labels=["<80", "80-150", "150-250", "250+"])
    rows = []
    for seg in ["room_type", "district", "capacity_band", "price_band"]:
        for lvl, g in t.groupby(seg, observed=True):
            if len(g) < 15:
                continue
            mb, mg = metrics(g.y, g.base), metrics(g.y, g.gbm)
            rows.append(dict(segment=seg, level=str(lvl), n=len(g), MAE_baseline=mb["MAE"], MAE_gbm=mg["MAE"],
                             MAPE_baseline=mb["MAPE"], MAPE_gbm=mg["MAPE"], bias_baseline=mb["bias"], bias_gbm=mg["bias"]))
    seg = pd.DataFrame(rows)
    seg.to_csv(ROOT / "reports" / "price_model_segment_errors.csv", index=False)

    # ---- SHAP -----------------------------------------------------------------------------------
    expl = shap.TreeExplainer(m)
    Xs = test[LISTING_FEATURES]
    sv = expl.shap_values(Xs)
    imp = pd.Series(np.abs(sv).mean(0), index=LISTING_FEATURES).sort_values(ascending=False)
    imp.to_csv(ROOT / "reports" / "price_model_shap_importance.csv", header=["mean_abs_shap_log_price"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    imp.head(12)[::-1].plot.barh(ax=ax, color="#2a6f97")
    ax.set(title="LightGBM: mean |SHAP| (effect on log price)", xlabel="mean |SHAP value|")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(IMG / "10_shap_importance.png", bbox_inches="tight", dpi=130); plt.close(fig)

    # error plot: baseline vs gbm by capacity band + price band
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for a, s in zip(ax, ["capacity_band", "price_band"]):
        d = seg[seg.segment == s].set_index("level")
        d[["MAPE_baseline", "MAPE_gbm"]].plot.bar(ax=a, color=["#8d99ae", "#2a6f97"], rot=0)
        a.set(title=f"MAPE by {s} (test)", ylabel="%", xlabel=""); a.spines[["top", "right"]].set_visible(False)
    fig.savefig(IMG / "11_model_error_segments.png", bbox_inches="tight", dpi=130); plt.close(fig)

    # ---- deployment model: refit on ALL benchmark listings, save everything V3 needs ------------
    mf = lgb_model(best_params, None).fit(df[LISTING_FEATURES], np.log(y))
    qs = {a: lgb.LGBMRegressor(objective="quantile", alpha=a, random_state=SEED, verbose=-1, n_jobs=4, cat_smooth=20,
                               min_data_per_group=20, cat_l2=10, **best_params).fit(df[LISTING_FEATURES], np.log(y)) for a in (0.1, 0.9)}
    bundle = {"model": mf, "q10": qs[0.1], "q90": qs[0.9], "features": LISTING_FEATURES,
              "categories": {c: list(df[c].cat.categories) for c in ["room_type", "property_type_grp", "district", "neighbourhood"]},
              "baseline": MedianBaseline(BASE_KEYS).fit(df, y), "trained_on": int(len(df)), "note": "refit on all benchmark listings; honest metrics come from the train/test protocol"}
    # ---- out-of-fold pricing gaps for Power BI (every listing is predicted by a model that never saw its host) ----
    oof_m, oof_b = np.zeros(len(df)), np.zeros(len(df))
    for tr, va in GroupKFold(n_splits=5).split(df, y, groups=df.host_key):
        oof_m[va] = np.exp(lgb_model(best_params, None).fit(df.iloc[tr][LISTING_FEATURES], np.log(y.iloc[tr])).predict(df.iloc[va][LISTING_FEATURES]))
        oof_b[va] = MedianBaseline(BASE_KEYS).fit(df.iloc[tr], y.iloc[tr]).predict(df.iloc[va])
    gap = pd.DataFrame({"listing_id": df.listing_id, "price_eur": y, "pred_price_model": oof_m.round(1), "pred_price_baseline": oof_b.round(1)})
    gap["gap_eur"] = (gap.price_eur - gap.pred_price_model).round(1)
    gap["gap_pct"] = (100 * gap.gap_eur / gap.pred_price_model).round(1)
    gap["pricing_position"] = pd.cut(gap.gap_pct, [-1000, -20, 20, 1000], labels=["below model (>20% under)", "in line (within 20%)", "above model (>20% over)"]).astype(str)
    (ROOT / "powerbi").mkdir(exist_ok=True)
    gap.to_csv(ROOT / "powerbi" / "fact_price_gap.csv", index=False, encoding="utf-8-sig")
    out["oof_gap"] = {"share_below": float((gap.gap_pct < -20).mean()), "share_inline": float(gap.gap_pct.between(-20, 20).mean()), "share_above": float((gap.gap_pct > 20).mean())}
    joblib.dump(bundle, MODEL_DIR / "price_model.joblib")
    (ROOT / "reports" / "price_model_metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_report(out, seg, imp)
    return out


def write_report(o, seg, imp):
    f = lambda d, k: f"{d[k]:.1f}"
    names = {"baseline_district_room": "Baseline: district x room-type median", "baseline_plus_capacity": "Baseline+: district x room-type x capacity median",
             "lightgbm_listing_features": "LightGBM (listing-only features)", "lightgbm_with_performance": "LightGBM + review/performance features (ablation)"}
    L = ["# Price model report (V2)", "",
         "Generated by `python -m src.price_model`. Target: nightly price (EUR) of benchmark listings (priced, short-stay, 10-1,000 EUR). "
         f"Train {o['n_train']:,} / test {o['n_test']:,} listings, split **by host** so no host appears on both sides. All tuning on train only (GroupKFold, 5 folds); test used once.", "",
         "## Metrics", "", "| Model | CV MAE | CV MAPE % | Test MAE (EUR) | Test MAPE % | Test median APE % | Test R2 (log) | Test bias (EUR) |", "|---|---|---|---|---|---|---|---|"]
    for k, n in names.items():
        c, t = o["cv"][k], o["test"][k]
        L.append(f"| {n} | {c['MAE']:.1f} | {c['MAPE']:.1f} | {t['MAE']:.1f} | {t['MAPE']:.1f} | {t['MdAPE']:.1f} | {t['R2_log']:.2f} | {t['bias']:.1f} |")
    L += ["", "## Does the model beat the baseline? (paired bootstrap on test MAE, 2,000 resamples)", ""]
    for k, v in o["bootstrap"].items():
        a, b = k.split("_minus_")
        L.append(f"- **{names[a]} minus {names[b]}**: mean MAE difference {v['mean_diff_MAE']:+.1f} EUR, 95% CI [{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}], "
                 f"share of resamples where the model is better {v['p_model_better']:.0%}.")
    base, gbm = o["test"]["baseline_district_room"], o["test"]["lightgbm_listing_features"]
    L += ["", f"**Reading:** on unseen hosts the LightGBM model has MAE {gbm['MAE']:.1f} EUR vs {base['MAE']:.1f} EUR for the district x room-type median "
          f"({100 * (1 - gbm['MAE'] / base['MAE']):.0f}% lower) and MAPE {gbm['MAPE']:.1f}% vs {base['MAPE']:.1f}%. "
          "Whether the improvement is reliable is decided by the bootstrap interval above, not by the point estimate.", "",
          f"80% prediction interval (q10-q90 quantile models): empirical test coverage **{o['interval_80pct']['test_coverage']:.0%}** (nominal 80%), median width {o['interval_80pct']['median_width_eur']:.0f} EUR.", "",
          "## Best hyper-parameters (random search, 14 trials)", "", f"`{o['best_params']}`", "",
          "## Feature importance (mean |SHAP|, effect on log price)", "", "| Feature | mean abs SHAP |", "|---|---|"]
    L += [f"| {k} | {v:.3f} |" for k, v in imp.head(10).items()]
    L += ["", "![SHAP](img/10_shap_importance.png)", "", "## Error analysis by segment (test set)", "",
          "| Segment | Level | n | MAE baseline | MAE LightGBM | MAPE baseline % | MAPE LightGBM % | bias baseline | bias LightGBM |", "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {r.segment} | {r.level} | {r.n} | {r.MAE_baseline:.1f} | {r.MAE_gbm:.1f} | {r.MAPE_baseline:.1f} | {r.MAPE_gbm:.1f} | {r.bias_baseline:+.1f} | {r.bias_gbm:+.1f} |" for r in seg.itertuples()]
    worse = seg[seg.MAPE_gbm > seg.MAPE_baseline]
    L += ["", "**Where LightGBM is not better (MAPE higher than baseline, segments with n >= 15):** " +
          ("; ".join(f"{r.segment}={r.level} ({r.MAPE_gbm:.1f}% vs {r.MAPE_baseline:.1f}%, n={r.n})" for r in worse.itertuples()) or "none") + ".",
          "Both models under-predict on average (negative bias): prices are right-skewed and the expensive tail is hard to predict from the available features. "
          "The 80% interval is too narrow (coverage below nominal), so present it as an approximate range, not a guarantee.",
          "The bootstrap resamples listings as independent although hosts are clustered, so the intervals are somewhat optimistic; the CV (grouped by host) points the same way.",
          "Price bands are defined on the actual price, so any model that shrinks toward the centre looks relatively better in the middle bands and worse in the tails; read the band rows with that in mind."]
    L += ["", "![segments](img/11_model_error_segments.png)", "",
          "## Limits (read before using the model)", "",
          "- Listed prices are asking prices, not transaction prices; the model predicts what comparable hosts ask, not what guests pay.",
          "- Features describe the listing, not its quality (photos, text, exact micro-location are not in the data); locations are anonymised to ~150 m.",
          "- Review/performance features are excluded from the main model because a new listing does not have them and they partly encode demand; the ablation row shows how much they would add.",
          "- Small test set (about 1,300 listings): differences of a few EUR are within noise, which is why the bootstrap is reported.",
          "- The saved model in `models/price_model.joblib` is re-fitted on all 6,456 benchmark listings for use in V3; the metrics above come from the held-out protocol, not from this refit.",
          "- Snapshot from 19 Sep 2026; prices move with season and events, which this release cannot model (calendar has no prices)."]
    (DOCS_DIR / "PRICE_MODEL_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    # import under the real module name so pickled objects (MedianBaseline) load from anywhere, e.g. the V3 app
    from src.price_model import main as _main
    _main()
