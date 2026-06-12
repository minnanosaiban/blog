"""
番外編B（機械学習）: 5 分足の次バー方向を勾配ブースティングで分類する。

blog20 のキャッシュ（data/blog20/close_wide.parquet 等）を再利用し、
同じ IN（〜2026-03-31）/ OUT（2026-04-01〜）分割で評価する。
ラベルは「次の 5 分バーの上下」。評価は AUC・的中率に加え、
確信度上位だけ取引した場合のコスト控除後 bps を主役にする。

出力: data/blog21/results_summary.json ほか
実行: python scripts/blog21_scalping_ml.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\stock_analysis")
CACHE = ROOT / "data" / "blog20"
OUT_DIR = ROOT / "data" / "blog21"
OUT_DIR.mkdir(parents=True, exist_ok=True)

IN_END = pd.Timestamp("2026-03-31")
COSTS_BP = [0, 5, 10]
UNIVERSE_N = 300
MIN_DAYS = 100

try:
    from lightgbm import LGBMClassifier as Booster
    BOOSTER_NAME = "LightGBM"
except ImportError:
    from sklearn.ensemble import HistGradientBoostingClassifier as Booster
    BOOSTER_NAME = "HistGradientBoosting (sklearn)"

from sklearn.metrics import roc_auc_score


def load_universe() -> tuple[pd.DataFrame, list[str]]:
    close = pd.read_parquet(CACHE / "close_wide.parquet")
    vol = pd.read_parquet(CACHE / "volume_wide.parquet")
    turnover = (close * vol).groupby(close.index.date).sum()
    days_ok = (close.notna().groupby(close.index.date).any()).sum() >= MIN_DAYS
    med = turnover[days_ok.index[days_ok]].median()
    uni = med.nlargest(UNIVERSE_N).index.tolist()
    return close, vol, uni


def build_dataset(close: pd.DataFrame, vol: pd.DataFrame,
                  uni: list[str]) -> pd.DataFrame:
    c = close[uni]
    v = vol[uni]
    dates = pd.Series(c.index.date, index=c.index)
    first_of_day = dates.ne(dates.shift())

    ret = c.pct_change(fill_method=None)
    ret[first_of_day.values] = np.nan

    feats = {
        "r1": ret,
        "r3": ret.rolling(3).sum(),
        "r6": ret.rolling(6).sum(),
        "r12": ret.rolling(12).sum(),
        "vol12": ret.rolling(12).std(),
        "vz": (v - v.rolling(12).mean()) / v.rolling(12).std(),
    }
    # 時間帯（バー位置）と当日のギャップ
    grp = c.groupby(dates.values)
    barpos_s = grp.cumcount().astype(float)
    day_open = grp.transform("first")
    pc = pd.DataFrame(np.where(first_of_day.values[:, None], c.shift(1).values, np.nan),
                      index=c.index, columns=c.columns)
    prev_close = pc.groupby(dates.values).transform("first")  # 当日最初のバーの前日終値
    gap = day_open / prev_close - 1

    label = (ret.shift(-1) > 0)
    valid = ret.shift(-1).notna() & (ret.shift(-1) != 0)

    frames = []
    for name, df in feats.items():
        s = df.stack(future_stack=True)
        s.name = name
        frames.append(s)
    X = pd.concat(frames, axis=1)
    X["barpos"] = np.repeat(barpos_s.values, len(uni))
    X["gap"] = gap.stack(future_stack=True)
    y = label.stack(future_stack=True)
    ok = valid.stack(future_stack=True)
    nxt = ret.shift(-1).stack(future_stack=True)

    data = X[ok].copy()
    data["y"] = y[ok].astype(int)
    data["next_ret"] = nxt[ok]
    data = data.dropna(subset=["r1", "r3", "r6", "vol12"])
    data = data.reset_index(names=["ts", "code"])
    return data


def main() -> None:
    close, vol, uni = load_universe()
    print(f"[universe] {len(uni)} 銘柄 / booster = {BOOSTER_NAME}")
    data = build_dataset(close, vol, uni)
    print(f"[dataset] {len(data):,} 行 × {data.shape[1]} 列")

    feat_cols = ["r1", "r3", "r6", "r12", "vol12", "vz", "barpos", "gap"]
    is_in = data["ts"] <= IN_END + pd.Timedelta(hours=23)
    # パージ: 境界日 1 日を学習から外す（リーク防止）
    purge = (data["ts"] > IN_END - pd.Timedelta(days=1)) & is_in
    train = data[is_in & ~purge]
    test = data[~is_in]
    print(f"[split] train {len(train):,} / test {len(test):,}")

    if BOOSTER_NAME == "LightGBM":
        model = Booster(n_estimators=300, learning_rate=0.05, num_leaves=63,
                        subsample=0.8, colsample_bytree=0.8, random_state=42)
    else:
        model = Booster(max_iter=300, learning_rate=0.05, max_leaf_nodes=63,
                        random_state=42)
    model.fit(train[feat_cols], train["y"])
    proba = model.predict_proba(test[feat_cols])[:, 1]

    auc = float(roc_auc_score(test["y"], proba))
    acc = float(((proba > 0.5).astype(int) == test["y"]).mean())
    base_majority = float(max(test["y"].mean(), 1 - test["y"].mean()))

    # 確信度十分位 → 平均次バーリターン（bps）。上位=買い、下位=売り
    t = test.copy()
    t["proba"] = proba
    t["dec"] = pd.qcut(t["proba"], 10, labels=False, duplicates="drop")
    dec_tbl = t.groupby("dec").agg(
        n=("next_ret", "size"), mean_bps=("next_ret", lambda s: s.mean() * 1e4),
        hit_up=("y", "mean")).round(3)
    dec_tbl.to_parquet(OUT_DIR / "decile_table.parquet")

    top = t[t["dec"] == t["dec"].max()]
    bot = t[t["dec"] == 0]
    long_bps = float(top["next_ret"].mean() * 1e4)
    short_bps = float(-bot["next_ret"].mean() * 1e4)
    ls_bps = (long_bps + short_bps) / 2

    # 特徴量重要度
    if hasattr(model, "feature_importances_"):
        imp = dict(zip(feat_cols, np.round(
            model.feature_importances_ / model.feature_importances_.sum(), 3).tolist()))
    else:
        imp = {}

    results = {
        "booster": BOOSTER_NAME,
        "n_train": int(len(train)), "n_test": int(len(test)),
        "auc_out": round(auc, 4),
        "accuracy_out": round(acc, 4),
        "baseline_majority": round(base_majority, 4),
        "decile_top_long_bps": round(long_bps, 3),
        "decile_bottom_short_bps": round(short_bps, 3),
        "long_short_avg_bps": round(ls_bps, 3),
        "net_bps_long_short": {f"{c}bp": round(ls_bps - c, 3) for c in COSTS_BP},
        "trades_per_side_out": int(len(top)),
        "feature_importance": imp,
        "decile_table": json.loads(dec_tbl.to_json(orient="index")),
    }
    out = OUT_DIR / "results_summary.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
