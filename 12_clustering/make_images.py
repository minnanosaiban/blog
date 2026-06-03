"""
連載 3-3 決算クラスタリング ― 画像生成スクリプト
入力: data/blog17/{clusters,profiles,silhouette}.csv
出力: docs/blog/posts/img/12_earnings_clustering/
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blog_style as bs

ROOT = Path(__file__).resolve().parent.parent
B17 = ROOT / "data" / "blog17"
OUT_DIR = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/12_earnings_clustering")
OUT_DIR.mkdir(parents=True, exist_ok=True)

bs.apply_rcparams()
FIG_W = bs.FIG_W

FC = ["net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
      "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
      "segment_count", "max_seg_share"]
JP = ["売上YoY", "営利YoY", "税引前YoY", "純利YoY", "包括YoY",
      "配当成長", "営業利益率", "純利益率", "ｾｸﾞﾒﾝﾄ数", "主力依存度"]
ORDER = ["A 急回復・高成長", "B 高収益・集中", "C 平均・安定"]
COLORS = {"A 急回復・高成長": "#E26A2C", "B 高収益・集中": "#A23B72", "C 平均・安定": "#6FA8D6"}


def image_01_silhouette():
    sil = pd.read_csv(B17 / "silhouette.csv")
    fig, ax = plt.subplots(figsize=(FIG_W, 5))
    ax.plot(sil["K"], sil["silhouette"], "o-", color="#2E86AB", lw=2, ms=8)
    k3 = sil[sil["K"] == 3]
    ax.scatter(k3["K"], k3["silhouette"], s=260, marker="o", facecolor="none",
               edgecolor="#E26A2C", lw=2.5, zorder=5)
    ax.annotate("採用 K=3\n（解釈しやすい3型）", (3, k3["silhouette"].iloc[0]),
                xytext=(24, 6), textcoords="offset points", fontsize=12,
                color="#E26A2C", weight="bold")
    ax.set_xlabel("クラスタ数 K")
    ax.set_ylabel("シルエット係数（高いほど分離が良い）")
    ax.set_title("クラスタ数の決定 ― K=2〜3 が高く、K≧4 で低下", pad=40)
    ax.set_xticks(sil["K"])
    ax.grid(alpha=0.3)
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "01_silhouette.png")
    plt.close(fig)
    print("saved 01_silhouette.png")


def image_02_cluster_map():
    df = pd.read_csv(B17 / "clusters.csv")
    df["code"] = df["code"].astype(str)
    fig, ax = plt.subplots(figsize=(FIG_W, 8))
    for t in ORDER:
        s = df[df["type"] == t]
        ax.scatter(s["pca_x"], s["pca_y"], s=30, alpha=0.6,
                   color=COLORS[t], label=f"{t}（{len(s)}社）")
    labels = {"5020": "ＥＮＥＯＳ", "7974": "任天堂", "8002": "丸紅", "6758": "ソニーG"}
    for code, nm in labels.items():
        r = df[df["code"] == code]
        if not r.empty:
            ax.scatter(r["pca_x"].iloc[0], r["pca_y"].iloc[0], s=260, marker="*",
                       edgecolor="black", facecolor="gold", lw=1.2, zorder=6)
            ax.annotate(nm, (r["pca_x"].iloc[0], r["pca_y"].iloc[0]),
                        xytext=(9, 8), textcoords="offset points", fontsize=12, weight="bold")
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("決算プロファイルの型マップ（PCA 2D 投影、PC1+PC2 = 47.6%）", pad=40)
    ax.legend(loc="best", framealpha=0.95)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "02_cluster_map.png")
    plt.close(fig)
    print("saved 02_cluster_map.png")


def image_03_profiles():
    df = pd.read_csv(B17 / "clusters.csv")

    def z(s):
        s = s.clip(-300, 300)
        med, std = s.median(), s.std()
        return (s - med) / std if std and std > 0 else s * 0

    Z = df[FC].apply(z)
    Z["type"] = df["type"]
    M = Z.groupby("type")[FC].mean().reindex(ORDER)

    fig, ax = plt.subplots(figsize=(FIG_W, 4.8))
    im = ax.imshow(M.to_numpy(), cmap="RdBu_r", vmin=-1.2, vmax=1.2, aspect="auto")
    ax.set_xticks(range(len(FC)))
    ax.set_xticklabels(JP, rotation=30, ha="right")
    ax.set_yticks(range(len(ORDER)))
    ax.set_yticklabels(ORDER)
    for i in range(len(ORDER)):
        for j in range(len(FC)):
            v = M.iloc[i, j]
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=10,
                    color="white" if abs(v) > 0.8 else "black")
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("母集団平均からの乖離（標準偏差）")
    ax.set_title("型ごとの決算プロファイル（赤＝平均より高い / 青＝低い）", pad=40)
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "03_profiles.png")
    plt.close(fig)
    print("saved 03_profiles.png")


def main():
    image_01_silhouette()
    image_02_cluster_map()
    image_03_profiles()
    print(f"\nAll saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
