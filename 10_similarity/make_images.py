"""
連載15 類似決算検索 ― 画像生成スクリプト

入力 : data/blog15/features.parquet, similarity_with_car_marubeni.csv, _sojitz.csv, events_2026.parquet
出力 : docs/blog/posts/img/15_similarity/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import numpy as np
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
        (0.3, 1.7, 2.2, 1.6, "1. 決算 JSON\n（連載08\nスキーマ）", "#6FA8D6"),
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

    ax.text(6.5, 4.75, "連載15: 数値特徴量ベクトル + コサイン類似度で「似た決算」を発見",
            ha="center", fontsize=24, weight="bold")
    ax.text(6.5, 0.85, "embedding API 不要・ローカル計算で完結。連載13 CAR と join すれば「過去類似決算の値動き」が分かる",
            ha="center", fontsize=18, color="#555", style="italic")
    ax.text(6.5, 0.30, "次回連載16 は本ロジックで「未来の値動き予測」フレームを構築",
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
    """丸紅 Top-15 + CAR を表形式の matplotlib 画像で。"""
    df = pd.read_csv(DATA_DIR / "similarity_with_car_marubeni.csv")
    df = df.head(15).copy()

    fig, ax = plt.subplots(figsize=(FIG_W, 7.5))
    ax.axis("off")
    ax.text(0.5, 1.02, "丸紅（8002）2026/3 期通期 に最も似た決算 Top-15 ＋ 各社の 2026/3 期 CAR",
            transform=ax.transAxes, ha="center", fontsize=14, weight="bold")

    cols = ["順位", "コード", "会社名", "類似度", "売上YoY", "純利YoY", "配当成長",
            "CAR[-1,+1]", "CAR[-1,+5]"]

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
            f"{r['car_m1_p1']:+.2f}%" if pd.notna(r['car_m1_p1']) else "—",
            f"{r['car_m1_p5']:+.2f}%" if pd.notna(r['car_m1_p5']) else "—",
        ])

    # 色分け：CAR がプラスなら緑、マイナスなら赤
    cell_colors = [["white"] * len(cols) for _ in rows]
    for i, r in df.iterrows():
        c5 = r.get("car_m1_p5")
        if pd.notna(c5):
            if c5 > 0:
                cell_colors[i][8] = "#E8F4EA"
            elif c5 < 0:
                cell_colors[i][8] = "#FEEBE8"

    # 会社名列に幅を寄せる（均等割だと長い社名が隣のセルへはみ出す）
    col_widths = [0.05, 0.07, 0.28, 0.08, 0.09, 0.09, 0.09, 0.115, 0.115]
    tbl = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                   cellColours=cell_colors, colWidths=col_widths,
                   colColours=["#2E86AB"] * len(cols))
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.0, 1.5)
    for j in range(len(cols)):
        cell = tbl[(0, j)]
        cell.get_text().set_color("white")
        cell.get_text().set_weight("bold")

    avg_car5 = df["car_m1_p5"].mean()
    win_rate = (df["car_m1_p5"] > 0).sum() / df["car_m1_p5"].notna().sum() * 100
    fig.text(0.5, 0.02,
             f"類似 Top-15 の 2026/3 期 平均 CAR[-1,+5] = {avg_car5:+.2f}% / 勝率 {win_rate:.1f}% "
             f"（参考：丸紅自身 = -9.39%）",
             ha="center", fontsize=12, color="#555", style="italic")
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "03_top15_marubeni.png")
    plt.close(fig)
    print("saved 03_top15_marubeni.png")


def image_04_car_distribution():
    """類似 Top-15 群の CAR 分布 vs クエリ銘柄自身。"""
    sim_m = pd.read_csv(DATA_DIR / "similarity_with_car_marubeni.csv")
    sim_s = pd.read_csv(DATA_DIR / "similarity_with_car_sojitz.csv")
    e2026 = pd.read_parquet(DATA_DIR / "events_2026.parquet")
    e2026["code"] = e2026["code"].astype(str)

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 5.5))

    for ax, sim_df, qcode, qname, color in [
        (axes[0], sim_m, "8002", "丸紅", "#2E86AB"),
        (axes[1], sim_s, "2768", "双日", "#E26A2C"),
    ]:
        c1 = sim_df["car_m1_p1"].dropna()
        c5 = sim_df["car_m1_p5"].dropna()
        x = np.arange(len(sim_df))
        ax.bar(x - 0.20, sim_df["car_m1_p1"], width=0.40, color="#A0C4D9", label="CAR[-1,+1]")
        ax.bar(x + 0.20, sim_df["car_m1_p5"], width=0.40, color=color, label="CAR[-1,+5]")
        ax.axhline(0, color="black", lw=0.6)
        ax.axhline(c5.mean(), color="green", lw=1.0, ls="--",
                   label=f"Top-15 平均 [-1,+5] = {c5.mean():+.2f}%")

        # クエリ銘柄自身の CAR
        own = e2026[e2026["code"] == qcode]
        if len(own):
            own_car5 = own["car_m1_p5"].iloc[0]
            ax.axhline(own_car5, color="red", lw=1.8, ls=":",
                       label=f"{qname} 自身 [-1,+5] = {own_car5:+.2f}%")

        ax.set_xticks(x)
        ax.set_xticklabels(sim_df["code"].astype(str), rotation=60, fontsize=8)
        ax.set_xlabel("類似 Top-15 銘柄コード")
        ax.set_ylabel("CAR（％）")
        ax.set_title(f"{qname}（{qcode}）の類似決算 Top-15 の CAR 分布",
                     pad=40)
        # 凡例がバーに被らないよう、凡例の分だけ上に空間を確保してから置く
        ylo, yhi = ax.get_ylim()
        ax.set_ylim(ylo, yhi + 0.55 * (yhi - ylo))
        ax.legend(loc="upper right", framealpha=0.95)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("「過去類似決算群の CAR 分布」と「クエリ銘柄自身の CAR」の比較",
                 y=1.02)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    bs.savefig_uniform(fig, OUT_DIR / "04_car_distribution.png")
    plt.close(fig)
    print("saved 04_car_distribution.png")


def image_05_numeric_vs_embedding():
    """数値特徴量 vs LLM embedding の対比図。"""
    fig, ax = plt.subplots(figsize=(FIG_W, 6.5))
    ax.set_xlim(0, 13); ax.set_ylim(0, 6.5); ax.axis("off")
    ax.text(6.5, 6.1, "数値特徴量 vs LLM embedding ― 用途別の使い分け",
            ha="center", fontsize=14, weight="bold")

    # Left: 数値特徴量
    _box(ax, 0.5, 4.6, 5.7, 1.0, "数値特徴量（本記事）", color="#2E86AB", fontsize=13)
    bullets_l = [
        "・ 10 次元（売上 YoY / 配当 / セグメント等）",
        "・ embedding API 不要・ローカル計算で完結",
        "・ 計算コスト: 0 円 / 1,000 銘柄 0.1 秒",
        "・ 解釈性: 高（次元名で説明可能）",
        "・ 限界: 数値化できないニュアンスは捕捉不可",
    ]
    for i, b in enumerate(bullets_l):
        ax.text(0.7, 4.2 - i * 0.45, b, fontsize=11, color="#222")

    # Right: LLM embedding
    _box(ax, 6.8, 4.6, 5.7, 1.0, "LLM embedding（次回以降）", color="#E26A2C", fontsize=13)
    bullets_r = [
        "・ 1,536〜3,072 次元（OpenAI text-embedding-3）",
        "・ 連載14 LLM 要約 → embedding に変換",
        "・ 計算コスト: 1 銘柄 ¥0.02〜0.10（OpenAI 公開価格）",
        "・ 解釈性: 低（次元の意味が分からない）",
        "・ 利点: 質的トピック（経営課題・戦略）も捕捉",
    ]
    for i, b in enumerate(bullets_r):
        ax.text(7.0, 4.2 - i * 0.45, b, fontsize=11, color="#222")

    # Bottom: 統合戦略
    ax.text(6.5, 1.5, "▼ 推奨アプローチ：両者をハイブリッドで使う ▼",
            ha="center", fontsize=12, weight="bold", color="#555")
    _box(ax, 0.5, 0.2, 12.0, 0.9,
         "1次フィルタ: 数値特徴量で高速に Top-50 を絞り込む → 2次精密化: LLM embedding で Top-10 に絞る",
         color="#A23B72", fontsize=12)

    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "05_numeric_vs_embedding.png")
    plt.close(fig)
    print("saved 05_numeric_vs_embedding.png")


def main():
    image_01_pipeline()
    image_02_feature_space()
    image_03_top15_table()
    image_04_car_distribution()
    image_05_numeric_vs_embedding()
    print(f"\nAll saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
