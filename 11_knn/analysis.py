"""
連載16 類似決算値動き予測 ― K-NN 回帰で「予測 CAR vs 実績 CAR」

入力:
  data/blog15/features.parquet     : 232 銘柄 × 10 次元特徴量
  data/blog15/events_2026.parquet  : 2026/3 期 announce の CAR

出力:
  data/blog16/predictions.csv   : 232 銘柄 × (K=5/15/30 の予測 + 実績)
  data/blog16/shocks.csv        : |予測 - 実績| の大きい順 Top-30（個別ショック）
  data/blog16/accuracy_by_K.csv : K ごとの RMSE / 相関 / 方向一致率
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
B15 = ROOT / "data" / "blog15"
OUT_DIR = ROOT / "data" / "blog16"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
    "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
    "segment_count", "max_seg_share",
]


def normalize(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        s = out[c].clip(-300, 300)
        med = s.median(); std = s.std()
        out[c] = (s - med) / std if std and std > 0 else 0
    return out


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


def main():
    print("=== Load features & events ===")
    feat = pd.read_parquet(B15 / "features.parquet")
    ev = pd.read_parquet(B15 / "events_2026.parquet")
    ev["code"] = ev["code"].astype(str)
    feat["code"] = feat["code"].astype(str)

    # 各 code について平均 CAR を取る（同期決算複数行ある場合の対策）
    ev_avg = ev.groupby("code")[["car_m1_p1", "car_m1_p5"]].mean().reset_index()
    print(f"  features: {len(feat)} / events: {len(ev)} / events by code: {len(ev_avg)}")

    # feat に actual CAR を merge
    df = feat.merge(ev_avg, on="code", how="left")
    df = df.dropna(subset=["car_m1_p5"]).copy()
    print(f"  merged with CAR: {len(df)} 銘柄")

    # 特徴量 >=7 個揃う銘柄に限定
    df = df.dropna(subset=FEATURE_COLS, thresh=7).reset_index(drop=True)
    print(f"  features >=7: {len(df)} 銘柄")

    # 正規化
    dfz = normalize(df, FEATURE_COLS)
    feats = dfz[FEATURE_COLS].fillna(0).to_numpy(dtype=float)

    print("=== Compute pairwise cosine similarity ===")
    n = len(dfz)
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s = cosine(feats[i], feats[j])
            sim_matrix[i, j] = s
            sim_matrix[j, i] = s
    print(f"  {n}x{n} similarity matrix computed")

    print("=== K-NN prediction (K=5, 15, 30) ===")
    ks = [5, 15, 30]
    preds = {f"pred_K{k}_p1": [] for k in ks}
    preds.update({f"pred_K{k}_p5": [] for k in ks})
    car_p1 = df["car_m1_p1"].to_numpy()
    car_p5 = df["car_m1_p5"].to_numpy()
    for i in range(n):
        sims = sim_matrix[i].copy()
        sims[i] = -np.inf  # 自分自身を除外
        order = np.argsort(-sims)
        for k in ks:
            top_idx = order[:k]
            preds[f"pred_K{k}_p1"].append(np.nanmean(car_p1[top_idx]))
            preds[f"pred_K{k}_p5"].append(np.nanmean(car_p5[top_idx]))
    for col, vals in preds.items():
        df[col] = vals

    # 予測誤差 (K=15 を中心に)
    df["err_K15_p5"] = df["car_m1_p5"] - df["pred_K15_p5"]
    df["err_K15_p1"] = df["car_m1_p1"] - df["pred_K15_p1"]
    df["abs_err_K15_p5"] = df["err_K15_p5"].abs()
    df["dir_match_K15_p5"] = ((df["car_m1_p5"] > 0) == (df["pred_K15_p5"] > 0)).astype(int)

    df.to_csv(OUT_DIR / "predictions.csv", index=False, encoding="utf-8-sig")
    print(f"  saved predictions.csv ({len(df)} rows)")

    print("=== Accuracy by K ===")
    rows = []
    for k in ks:
        for win in ["p1", "p5"]:
            actual = df[f"car_m1_{win}"]
            pred = df[f"pred_K{k}_{win}"]
            rmse = np.sqrt(((actual - pred) ** 2).mean())
            mae = (actual - pred).abs().mean()
            corr = actual.corr(pred)
            dir_match = ((actual > 0) == (pred > 0)).mean() * 100
            rows.append({
                "K": k, "window": f"[-1,+{1 if win=='p1' else 5}]",
                "n": len(df), "RMSE": rmse, "MAE": mae,
                "corr": corr, "dir_match_pct": dir_match,
                "actual_mean": actual.mean(), "pred_mean": pred.mean(),
            })
    accdf = pd.DataFrame(rows)
    accdf.to_csv(OUT_DIR / "accuracy_by_K.csv", index=False, encoding="utf-8-sig")
    print(accdf.to_string())

    print("=== Individual shocks (|err_K15_p5| Top 30) ===")
    shocks = df.sort_values("abs_err_K15_p5", ascending=False).head(30)
    cols_show = ["code", "company", "car_m1_p1", "car_m1_p5",
                 "pred_K15_p1", "pred_K15_p5", "err_K15_p5",
                 "net_sales_yoy", "net_income_yoy", "div_growth_pct"]
    shocks[cols_show].to_csv(OUT_DIR / "shocks.csv", index=False, encoding="utf-8-sig")
    print(shocks[["code", "company", "car_m1_p5", "pred_K15_p5", "err_K15_p5"]].to_string())

    print("=== Narrative 5 highlight ===")
    narr5 = ["8002", "2768", "5020", "5019", "5021"]
    n5 = df[df["code"].isin(narr5)]
    print(n5[["code", "company", "car_m1_p1", "car_m1_p5", "pred_K15_p1", "pred_K15_p5",
              "err_K15_p5"]].to_string())

    # ── ENEOS 単独 ad-hoc 計算（[-1,+5] 不足のため [-1,+1] のみで K-NN 予測） ──
    print("=== ENEOS 5020 ad-hoc K-NN ([-1,+1] only) ===")
    feat_all = pd.read_parquet(B15 / "features.parquet")
    feat_all["code"] = feat_all["code"].astype(str)
    en_row = feat_all[(feat_all["code"] == "5020") &
                      (feat_all["period_end"] == "2026-03-31")]
    if not en_row.empty:
        # ENEOS 含めて features を再正規化
        feat_full = feat_all.dropna(subset=FEATURE_COLS, thresh=7).reset_index(drop=True)
        feat_full_z = normalize(feat_full, FEATURE_COLS)
        feat_arr = feat_full_z[FEATURE_COLS].fillna(0).to_numpy(dtype=float)
        en_idx = feat_full_z[feat_full_z["code"] == "5020"].index[0]
        en_vec = feat_arr[en_idx]
        sims = np.array([cosine(en_vec, feat_arr[j]) for j in range(len(feat_arr))])
        sims[en_idx] = -np.inf
        topk = np.argsort(-sims)[:15]
        # 各類似銘柄の [-1,+1] CAR（events_2026 から）
        codes_top = feat_full.iloc[topk]["code"].tolist()
        ev_p1 = ev.groupby("code")["car_m1_p1"].mean()
        pred_p1 = np.nanmean([ev_p1.get(c, np.nan) for c in codes_top])
        # ENEOS 自身の CAR [-1,+1]
        en_car_p1 = ev_p1.get("5020", np.nan)
        err_p1 = en_car_p1 - pred_p1 if pd.notna(en_car_p1) and pd.notna(pred_p1) else np.nan
        print(f"  ENEOS 5020: 実績 CAR[-1,+1] = {en_car_p1:+.2f}%, "
              f"K-NN(15) 予測 = {pred_p1:+.2f}%, 誤差 = {err_p1:+.2f}pp")
        print(f"  → 個別ショック判定: {'ポジショック' if err_p1 > 5 else 'ネガショック' if err_p1 < -5 else '中庸'}")
    else:
        print("  ENEOS features 未取得")

    print("=== Baseline: 全銘柄平均 を予測値とした場合 ===")
    baseline_pred_p5 = df["car_m1_p5"].mean()
    baseline_rmse = np.sqrt(((df["car_m1_p5"] - baseline_pred_p5) ** 2).mean())
    print(f"  baseline pred = {baseline_pred_p5:+.3f}, RMSE = {baseline_rmse:.3f}")
    print(f"  K=15 RMSE     = {accdf[(accdf['K']==15) & (accdf['window']=='[-1,+5]')]['RMSE'].iloc[0]:.3f}")
    print(f"  → K-NN による誤差削減 = {(baseline_rmse - accdf[(accdf['K']==15) & (accdf['window']=='[-1,+5]')]['RMSE'].iloc[0]):.3f}")

    print("=== DONE ===")


if __name__ == "__main__":
    main()
