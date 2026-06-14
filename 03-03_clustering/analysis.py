"""
連載 3-3 決算クラスタリング ― KMeans で「決算の型」を発見

入力:
  data/blog15/features.parquet     : 決算 10 次元特徴量
出力:
  data/blog17/clusters.csv         : 銘柄 × (cluster, type, pca_x, pca_y, 特徴量)
  data/blog17/profiles.csv         : 型ごとの平均特徴量 + 社数
  data/blog17/silhouette.csv       : K ごとのシルエット係数
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parent.parent
B15 = ROOT / "data" / "blog15"
OUT = ROOT / "data" / "blog17"
OUT.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
    "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
    "segment_count", "max_seg_share",
]
K = 3
SEED = 42


def normalize(df: pd.DataFrame, cols) -> pd.DataFrame:
    """3-1/3-2 と同じ前処理: ±300 で clip → median/std で z-score。"""
    out = df.copy()
    for c in cols:
        s = out[c].clip(-300, 300)
        med = s.median(); std = s.std()
        out[c] = (s - med) / std if std and std > 0 else 0
    return out


def main():
    print("=== Load features ===")
    feat = pd.read_parquet(B15 / "features.parquet")
    feat["code"] = feat["code"].astype(str)
    df = feat.dropna(subset=FEATURE_COLS, thresh=7).reset_index(drop=True)
    dups = int(df["code"].duplicated().sum())
    print(f"  n = {len(df)} 銘柄 (dup codes: {dups})")

    dfz = normalize(df, FEATURE_COLS)
    X = dfz[FEATURE_COLS].fillna(0).to_numpy(dtype=float)

    print("=== Silhouette sweep ===")
    sil_rows = []
    for k in range(2, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X)
        sc = silhouette_score(X, km.labels_)
        sil_rows.append({"K": k, "silhouette": round(float(sc), 4)})
        print(f"  K={k}: silhouette={sc:.3f}")
    pd.DataFrame(sil_rows).to_csv(OUT / "silhouette.csv", index=False, encoding="utf-8-sig")

    print(f"=== KMeans (K={K}) ===")
    km = KMeans(n_clusters=K, n_init=10, random_state=SEED).fit(X)
    df["cluster"] = km.labels_

    pca = PCA(n_components=2, random_state=SEED).fit(X)
    xy = pca.transform(X)
    df["pca_x"] = xy[:, 0]
    df["pca_y"] = xy[:, 1]
    pc = pca.explained_variance_ratio_[:2]
    print(f"  PCA var: PC1={pc[0]:.3f} PC2={pc[1]:.3f} sum={pc.sum():.3f}")

    # 型名をプロファイルから決定（クラスタ番号は乱数依存なので意味で固定）
    prof = df.groupby("cluster")[FEATURE_COLS].mean()
    prof["n"] = df.groupby("cluster").size()
    recov = prof["net_income_yoy"].idxmax()   # 純利益 YoY 最大 → 急回復
    highm = prof["op_margin"].idxmax()         # 営業利益率 最大 → 高収益
    type_map = {recov: "A 急回復・高成長", highm: "B 高収益・集中"}
    for c in prof.index:
        type_map.setdefault(c, "C 平均・安定")
    df["type"] = df["cluster"].map(type_map)
    prof["type"] = [type_map[c] for c in prof.index]

    out_cols = ["code", "company", "period_end", "cluster", "type", "pca_x", "pca_y"] + FEATURE_COLS
    df[out_cols].to_csv(OUT / "clusters.csv", index=False, encoding="utf-8-sig")
    prof.round(2).to_csv(OUT / "profiles.csv", encoding="utf-8-sig")

    print("=== Cluster profiles (raw means) ===")
    print(prof.round(1).to_string())

    print("=== Key stocks ===")
    for code in ["5020", "8002", "2768", "7974", "6758"]:
        r = df[df["code"] == code]
        if not r.empty:
            print(f"  {code} {r['company'].iloc[0][:10]} -> {r['type'].iloc[0]}")
        else:
            print(f"  {code} (not in filtered set)")
    print("=== DONE ===")


if __name__ == "__main__":
    main()
