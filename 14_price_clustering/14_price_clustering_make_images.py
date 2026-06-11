# -*- coding: utf-8 -*-
"""
連載 3-5 値動きクラスタリング ― 画像生成（hotline の img フォルダへ出力）

入力:
  data/blog15/features.parquet            : 3 章ユニバース（code / company）
  data/prices/stocks/daily/{code}.parquet : 日次 Close（auto_adjust 済み）
  data/master/sectors/*.csv               : code -> セクター名
出力:
  docs/blog/posts/img/14_price_clustering/ : 00_thumbnail / 01_corr_heatmap /
                                             02_stock_map / 03_near_identical
  data/blog19/clusters.csv, near_identical_pairs.csv

予測ではなく「記述・発見」。3-2/3-4 が失敗した予測タスクではない。
"""
from __future__ import annotations

import sys
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster, leaves_list
from scipy.spatial.distance import squareform
from sklearn.manifold import MDS

import _blog_style as bs

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
B15 = ROOT / "data" / "blog15"
DAILY = ROOT / "data" / "prices" / "stocks" / "daily"
SECT = ROOT / "data" / "master" / "sectors"
DATA_OUT = ROOT / "data" / "blog19"
IMG = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/14_price_clustering")
DATA_OUT.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

WINDOW = 500
MIN_COVER = 0.95
NEAR_RHO = 0.90
N_CLUSTERS = 12
ENEOS, IDEMITSU, COSMO = "5020", "5019", "5021"
FEATURE_COLS = [
    "net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
    "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
    "segment_count", "max_seg_share",
]
SPOTLIGHT = {ENEOS: "ENEOS", IDEMITSU: "出光", COSMO: "コスモ", "8002": "丸紅",
             "2768": "双日", "7203": "トヨタ", "6758": "ソニーG", "8306": "三菱UFJ",
             "9501": "東電", "9984": "SBG"}
# 銘柄マップで近接マーカーと被らないようラベルごとに引き出し方向を変える
SPOT_OFFSET = {"2768": (6, -16)}  # 双日: 右上に置くと丸紅マーカーに接触する


def short_name(code: str, name: dict, width: int = 6) -> str:
    """y軸ラベル用の短縮社名。法人格を落とし、欠損は SPOTLIGHT/コードで補う。"""
    s = name.get(code) or SPOTLIGHT.get(code) or code
    s = str(s)
    if s == "nan":
        s = SPOTLIGHT.get(code, code)
    for tok in ("株式会社", "（株）", "(株)"):
        s = s.replace(tok, "")
    s = (s.replace("ホールディングス", "HD").replace("ホールディング", "HD")
          .replace("フィナンシャルグループ", "FG").replace("グループ", "G")
          .strip())
    return s if len(s) <= width else s[: width - 1] + "…"


def load_universe():
    feat = pd.read_parquet(B15 / "features.parquet")
    feat["code"] = feat["code"].astype(str)
    uni = feat.dropna(subset=FEATURE_COLS, thresh=7)
    name = dict(zip(uni["code"], uni["company"].astype(str)))
    codes = [c for c in uni["code"] if (DAILY / f"{c}.parquet").exists()]
    for c in [IDEMITSU, COSMO] + list(SPOTLIGHT):
        if c not in codes and (DAILY / f"{c}.parquet").exists():
            codes.append(c)
    return codes, name


def load_sectors():
    code2sec = {}
    for csv in SECT.glob("*.csv"):
        try:
            df = pd.read_csv(csv, encoding="utf-8", dtype=str)
        except Exception:
            continue
        if df.shape[1] < 4:
            continue
        cc, sc = df.columns[0], df.columns[3]
        for _, r in df.iterrows():
            c = str(r[cc]).strip()
            if c and c not in code2sec:
                code2sec[c] = str(r[sc]).strip()
    return code2sec


def build_returns(codes):
    closes = {}
    for c in codes:
        try:
            closes[c] = pd.read_parquet(DAILY / f"{c}.parquet")["Close"].astype(float)
        except Exception:
            continue
    px = pd.DataFrame(closes).sort_index().tail(WINDOW)
    cover = px.notna().mean()
    px = px.loc[:, cover[cover >= MIN_COVER].index]
    return np.log(px).diff().iloc[1:].ffill().fillna(0.0)


def main():
    bs.apply_rcparams()
    FIG_W = bs.FIG_W
    codes, name = load_universe()
    code2sec = load_sectors()
    rets = build_returns(codes)
    cols = list(rets.columns)
    print(f"銘柄 {len(cols)} / 営業日 {len(rets)}  期間 {rets.index.min().date()}..{rets.index.max().date()}")

    corr = rets.corr()
    D = np.sqrt(np.clip(2.0 * (1.0 - corr.values), 0, None))
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="ward")
    labels = fcluster(Z, t=N_CLUSTERS, criterion="maxclust")
    order = leaves_list(Z)
    clab = dict(zip(cols, labels))

    cl_df = pd.DataFrame({"code": cols, "cluster": labels})
    cl_df["sector"] = cl_df["code"].map(code2sec).fillna("（不明）")
    cl_df["company"] = cl_df["code"].map(name).fillna(cl_df["code"])
    print("\n=== クラスタ別の優勢セクター（業種コード不使用） ===")
    for k, g in cl_df.groupby("cluster"):
        known = g[g["sector"] != "（不明）"]
        if len(known):
            top = known["sector"].value_counts().head(2)
            secs = ", ".join(f"{s}×{n}" for s, n in top.items())
        else:
            secs = "（セクター辞書に未登録）"
        print(f"  C{k:2d} n={len(g):3d}  {secs}")

    # near-identical pairs
    cm = corr.values
    iu = np.triu_indices_from(cm, k=1)
    pairs = pd.DataFrame({"a": np.array(cols)[iu[0]], "b": np.array(cols)[iu[1]], "rho": cm[iu]}).sort_values("rho", ascending=False)
    pairs["a_name"] = pairs["a"].map(name); pairs["b_name"] = pairs["b"].map(name)
    pairs["a_sec"] = pairs["a"].map(code2sec); pairs["b_sec"] = pairs["b"].map(code2sec)
    for th in (0.90, 0.85, 0.80, 0.75):
        print(f"  相関 >= {th:.2f}: {int((pairs['rho'] >= th).sum())} ペア")
    print("\n=== 最も連動するペア Top12 ===")
    for _, r in pairs.head(12).iterrows():
        print(f"  ρ={r.rho:.3f}  {r.a} {str(r.a_name)[:10]:<10} ─ {r.b} {str(r.b_name)[:10]:<10} [{r.a_sec}/{r.b_sec}]")

    # MDS 座標
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42,
              normalized_stress="auto", n_init=2, max_iter=300)
    xy = mds.fit_transform(D)
    cl_df["x"], cl_df["y"] = xy[:, 0], xy[:, 1]
    cl_df.to_csv(DATA_OUT / "clusters.csv", index=False, encoding="utf-8-sig")
    pairs.head(60).to_csv(DATA_OUT / "near_identical_pairs.csv", index=False, encoding="utf-8-sig")
    idx = {c: i for i, c in enumerate(cols)}

    # ---- 01 相関ヒートマップ ----
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.72))
    im = ax.imshow(corr.values[np.ix_(order, order)], cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_title(f"値動き相関ヒートマップ（クラスタ順に並べ替え・{len(cols)}銘柄）", fontsize=15)
    ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.01, label="日次リターン相関 ρ")
    bs.savefig_uniform(fig, IMG / "01_corr_heatmap.png")

    # ---- 02 銘柄マップ ----
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.72))
    ax.scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab20", s=44, alpha=0.8, edgecolors="white", linewidths=0.4)
    for c, lab in SPOTLIGHT.items():
        if c in idx:
            i = idx[c]
            ax.annotate(lab, (xy[i, 0], xy[i, 1]), fontsize=11, fontweight="bold",
                        xytext=SPOT_OFFSET.get(c, (4, 4)), textcoords="offset points")
            ax.scatter([xy[i, 0]], [xy[i, 1]], s=92, facecolors="none", edgecolors="black", linewidths=1.2)
    ax.set_title("値動き銘柄マップ（相関距離を MDS で2次元化・色＝自動クラスタ）", fontsize=15)
    ax.set_xticks([]); ax.set_yticks([])
    bs.savefig_uniform(fig, IMG / "02_stock_map.png")

    # ---- 03 ほぼ同一ペア Top15 ----
    n_near80 = int((pairs["rho"] >= 0.80).sum())
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.6))
    top = pairs.head(15).iloc[::-1]
    ylab = [f"{a} {short_name(a, name)} ─ {b} {short_name(b, name)}"
            for a, b in zip(top.a, top.b)]
    ax.barh(range(len(top)), top.rho, color="#c0504d")
    ax.set_yticks(range(len(top))); ax.set_yticklabels(ylab, fontsize=14)
    ax.set_xlim(0.7, 0.9); ax.set_xlabel("日次リターン相関 ρ")
    ax.set_title(f"最も連動する値動きペア Top15（ρ≥0.80 は {n_near80} ペア）", fontsize=15)
    for i, v in enumerate(top.rho):
        ax.text(v - 0.003, i, f"{v:.3f}", va="center", ha="right", color="white", fontsize=13)
    bs.savefig_uniform(fig, IMG / "03_near_identical.png")

    # ---- 00 サムネイル（銘柄マップ・タイトル入り） ----
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.5))
    ax.scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab20", s=70, alpha=0.78, edgecolors="white", linewidths=0.5)
    for c in (ENEOS, IDEMITSU, COSMO, "8002"):
        if c in idx:
            i = idx[c]
            ax.scatter([xy[i, 0]], [xy[i, 1]], s=120, facecolors="none", edgecolors="black", linewidths=1.4)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.02, 0.96, "値動きクラスタリング", transform=ax.transAxes, fontsize=30, fontweight="bold", va="top")
    ax.text(0.02, 0.82, "業種コードを使わず、値動きだけで仲間を見つける", transform=ax.transAxes, fontsize=15, va="top", color="#444")
    bs.savefig_uniform(fig, IMG / "00_thumbnail.png")

    print(f"\n画像: {IMG}")


if __name__ == "__main__":
    main()
