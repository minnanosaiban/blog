"""
連載15 類似決算検索 ― 画像生成スクリプト

入力 : data/blog15/features.parquet, similarity_with_car_marubeni.csv, _sojitz.csv
出力 : docs/blog/posts/img/15_similarity/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import pandas as pd
from sklearn.decomposition import PCA

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blog_style as bs

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "blog15"
OUT_DIR = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/10_similar_earnings_search")
OUT_DIR.mkdir(parents=True, exist_ok=True)

bs.apply_rcparams()
FIG_W = bs.FIG_W

FEATURE_COLS = [
    "net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
    "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
    "segment_count", "max_seg_share",
]


def _box(ax, x, y, w, h, text, color="#2E86AB", tcolor="white", fontsize=11, weight="bold"):
    b = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                linewidth=1.5, facecolor=color, edgecolor="#1a4d6e", alpha=0.92)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=tcolor, fontsize=fontsize, weight=weight)


def _arrow(ax, x1, y1, x2, y2, color="#444"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=1.8, color=color))


def image_01_pipeline():
    fig, ax = plt.subplots(figsize=(FIG_W, 5.4))
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.4); ax.axis("off")
    steps = [
        (0.3, 1.7, 2.2, 1.6, "1. 決算 JSON\n（1-3\nスキーマ）", "#6FA8D6"),
        (2.9, 1.7, 2.2, 1.6, "2. 特徴量\n抽出\n（10 次元）", "#2E86AB"),
        (5.5, 1.7, 2.2, 1.6, "3. z-score\n正規化", "#E26A2C"),
        (8.1, 1.7, 2.2, 1.6, "4. cosine\n類似度", "#A23B72"),
        (10.7, 1.7, 2.0, 1.6, "5. Top-K\n類似決算", "#48A14D"),
    ]
    for x, y, w, h, t, c in steps:
        _box(ax, x, y, w, h, t, color=c, fontsize=20)
    for i in range(len(steps) - 1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i + 1][0]
        _arrow(ax, x1, 2.5, x2, 2.5)

    ax.text(6.5, 4.75, "数値特徴量ベクトル + コサイン類似度で「似た決算」を発見",
            ha="center", fontsize=24, weight="bold")
    ax.text(6.5, 0.85, "CAR（2-7）と join すれば「過去類似決算の値動き」が分かる",
            ha="center", fontsize=18, color="#555", style="italic")
    ax.text(6.5, 0.30, "次回（3-2）は本ロジックで「個別ショックの検出」フレームを構築",
            ha="center", fontsize=16, color="#666")
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "01_pipeline.png")
    plt.close(fig)
    print("saved 01_pipeline.png")


def image_02_feature_space():
    """PCA で 10 次元特徴量を 2D 投影。丸紅/双日と類似 Top-5 を強調。"""
    df = pd.read_parquet(DATA_DIR / "features.parquet")
    df = df.dropna(subset=FEATURE_COLS, thresh=7).copy()
    # 同 normalize ロジック
    X = df[FEATURE_COLS].copy()
    for c in X.columns:
        s = X[c].clip(-300, 300)
        med = s.median(); std = s.std()
        X[c] = (s - med) / std if std > 0 else 0
    X = X.fillna(0)
    pca = PCA(n_components=2, random_state=0)
    pcs = pca.fit_transform(X.to_numpy())
    df["pc1"] = pcs[:, 0]
    df["pc2"] = pcs[:, 1]

    sim_m = pd.read_csv(DATA_DIR / "similarity_with_car_marubeni.csv")
    sim_s = pd.read_csv(DATA_DIR / "similarity_with_car_sojitz.csv")
    sim_m["code"] = sim_m["code"].astype(str)
    sim_s["code"] = sim_s["code"].astype(str)

    fig, ax = plt.subplots(figsize=(FIG_W, 8))
    ax.scatter(df["pc1"], df["pc2"], s=12, alpha=0.20, color="#888", label=f"全 {len(df)} 銘柄")

    # Top-5 highlight
    top5_m = sim_m.head(5)
    top5_s = sim_s.head(5)
    df["code"] = df["code"].astype(str)
    mask_m = df["code"].isin(top5_m["code"])
    mask_s = df["code"].isin(top5_s["code"])
    ax.scatter(df.loc[mask_m, "pc1"], df.loc[mask_m, "pc2"], s=120, edgecolor="black",
               facecolor="#2E86AB", lw=0.7, label="丸紅 Top-5 類似", zorder=4)
    ax.scatter(df.loc[mask_s, "pc1"], df.loc[mask_s, "pc2"], s=120, edgecolor="black",
               facecolor="#E26A2C", marker="s", lw=0.7, label="双日 Top-5 類似", zorder=4)

    # クエリ銘柄を強調
    for code, name, color, marker in [("8002", "丸紅", "#A23B72", "*"),
                                      ("2768", "双日", "#48A14D", "*")]:
        sub = df[df["code"] == code]
        if len(sub):
            ax.scatter(sub["pc1"], sub["pc2"], s=400, marker=marker,
                       edgecolor="black", facecolor=color, lw=1.5, label=name, zorder=5)

    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% 分散)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% 分散)")
    ax.set_title("10 次元特徴量空間の 2D 投影（PCA）― 類似決算は空間上で近接する",
                 pad=40)
    ax.legend(loc="upper right", framealpha=0.92)
    ax.grid(alpha=0.25)
    ax.axhline(0, color="black", lw=0.4)
    ax.axvline(0, color="black", lw=0.4)
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "02_feature_space_pca.png")
    plt.close(fig)
    print("saved 02_feature_space_pca.png")


def image_03_top15_table():
    """丸紅 Top-15（コサイン類似度のみ）を表形式の matplotlib 画像で。"""
    df = pd.read_csv(DATA_DIR / "similarity_with_car_marubeni.csv")
    df = df.head(15).copy()

    fig, ax = plt.subplots(figsize=(FIG_W, 7.5))
    ax.axis("off")
    ax.text(0.5, 1.02, "丸紅（8002）2026/3 期通期 に最も似た決算 Top-15（コサイン類似度）",
            transform=ax.transAxes, ha="center", fontsize=14, weight="bold")

    cols = ["順位", "コード", "会社名", "類似度", "売上YoY", "純利YoY", "配当成長"]

    def _name(s: str) -> str:
        """法人格を落として列幅に収める（長い社名がセル罫線を跨ぐのを防ぐ）。"""
        s = str(s).replace("株式会社", "").strip()
        return s if len(s) <= 14 else s[:13] + "…"

    rows = []
    for i, r in df.iterrows():
        rows.append([
            str(i + 1),
            str(r["code"]),
            _name(r["company"]),
            f"{r['similarity']:.3f}",
            f"{r['net_sales_yoy']:+.1f}%" if pd.notna(r['net_sales_yoy']) else "—",
            f"{r['net_income_yoy']:+.1f}%" if pd.notna(r['net_income_yoy']) else "—",
            f"{r['div_growth_pct']:+.1f}%" if pd.notna(r['div_growth_pct']) else "—",
        ])

    # 会社名列に幅を寄せる（均等割だと長い社名が隣のセルへはみ出す）
    col_widths = [0.06, 0.10, 0.34, 0.12, 0.13, 0.13, 0.12]
    tbl = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                   colWidths=col_widths,
                   colColours=["#2E86AB"] * len(cols))
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.5)
    for j in range(len(cols)):
        cell = tbl[(0, j)]
        cell.get_text().set_color("white")
        cell.get_text().set_weight("bold")

    fig.text(0.5, 0.04,
             "業種コードを使わず、決算 10 指標のコサイン類似度のみで抽出 ― それでも総合商社が自然に上位へ",
             ha="center", fontsize=12, color="#555", style="italic")
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "03_top15_marubeni.png")
    plt.close(fig)
    print("saved 03_top15_marubeni.png")


def main():
    image_01_pipeline()
    image_02_feature_space()
    image_03_top15_table()
    print(f"\nAll saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
