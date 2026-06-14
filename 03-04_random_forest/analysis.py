"""
連載 3-4 ランダムフォレスト ― 「市場の反応に効く決算指標」を特徴量重要度で探る

問い: 決算 10 指標から CAR の方向（上 / 下）を予測できるか？
結論の見込み: 予測精度はベースライン並み（＝当てられない、3-2 と整合）。
            だが「特徴量重要度」で “市場がどの指標を重く見るか” が分かる＝発見。

入力:
  data/blog15/features.parquet     : 決算 10 次元特徴量
  data/blog15/events_2026.parquet  : 2026/3 期 announce の CAR
出力:
  data/blog18/importance.csv       : 特徴量重要度（impurity + permutation）
  data/blog18/accuracy.csv         : 精度（CV / test / baseline / AUC）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

ROOT = Path(__file__).resolve().parent.parent
B15 = ROOT / "data" / "blog15"
OUT = ROOT / "data" / "blog18"
OUT.mkdir(parents=True, exist_ok=True)

FC = ["net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
      "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
      "segment_count", "max_seg_share"]
SEED = 42


def main():
    print("=== Load features + CAR ===")
    feat = pd.read_parquet(B15 / "features.parquet"); feat["code"] = feat["code"].astype(str)
    ev = pd.read_parquet(B15 / "events_2026.parquet"); ev["code"] = ev["code"].astype(str)
    ev_avg = ev.groupby("code")[["car_m1_p1", "car_m1_p5"]].mean().reset_index()
    df = feat.merge(ev_avg, on="code", how="left").dropna(subset=["car_m1_p5"])
    df = df.dropna(subset=FC, thresh=7).reset_index(drop=True)

    X = df[FC].clip(-300, 300)
    X = X.fillna(X.median()).to_numpy(dtype=float)
    y = (df["car_m1_p5"] > 0).astype(int).to_numpy()
    n = len(df)
    pos = y.mean()
    baseline = max(pos, 1 - pos)
    print(f"  n = {n}, 上昇率 = {pos:.3f}, baseline(多数派) acc = {baseline:.3f}")

    print("=== CV accuracy / AUC (5-fold) ===")
    rf = RandomForestClassifier(n_estimators=400, random_state=SEED, n_jobs=-1)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    acc = cross_val_score(rf, X, y, cv=cv, scoring="accuracy")
    auc = cross_val_score(rf, X, y, cv=cv, scoring="roc_auc")
    print(f"  CV accuracy = {acc.mean():.3f} ± {acc.std():.3f}")
    print(f"  CV AUC      = {auc.mean():.3f} ± {auc.std():.3f}")

    print("=== Holdout (70/30) + permutation importance ===")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)
    rf.fit(Xtr, ytr)
    yhat = rf.predict(Xte)
    test_acc = accuracy_score(yte, yhat)
    test_auc = roc_auc_score(yte, rf.predict_proba(Xte)[:, 1])
    print(f"  test accuracy = {test_acc:.3f}, test AUC = {test_auc:.3f}")
    perm = permutation_importance(rf, Xte, yte, n_repeats=30, random_state=SEED, scoring="accuracy")

    imp = pd.DataFrame({
        "feature": FC,
        "impurity": rf.feature_importances_,
        "perm_mean": perm.importances_mean,
        "perm_std": perm.importances_std,
    }).sort_values("perm_mean", ascending=False).reset_index(drop=True)
    imp.to_csv(OUT / "importance.csv", index=False, encoding="utf-8-sig")
    print(imp.round(4).to_string())

    pd.DataFrame([{
        "n": n, "pos_rate": pos, "baseline_acc": baseline,
        "cv_acc": acc.mean(), "cv_acc_std": acc.std(),
        "cv_auc": auc.mean(), "cv_auc_std": auc.std(),
        "test_acc": test_acc, "test_auc": test_auc,
    }]).to_csv(OUT / "accuracy.csv", index=False, encoding="utf-8-sig")

    print("=== ENEOS 5020 ===")
    r = df[df["code"] == "5020"]
    if not r.empty:
        idx = r.index[0]
        prob_up = rf.predict_proba(X[idx:idx + 1])[0, 1]
        print(f"  ENEOS 実績CAR[-1,+5] = {df.loc[idx,'car_m1_p5']:+.2f}% "
              f"(方向 {'上' if y[idx] else '下'}), RF 上昇確率 = {prob_up:.2f}")
    print("=== DONE ===")


if __name__ == "__main__":
    main()
