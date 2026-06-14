"""
連載16 類似決算値動き予測 ― 画像生成スクリプト
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blog_style as bs

ROOT = Path(__file__).resolve().parent.parent
B16 = ROOT / "data" / "blog16"
OUT_DIR = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/11_knn_prediction")
OUT_DIR.mkdir(parents=True, exist_ok=True)

bs.apply_rcparams()
FIG_W = bs.FIG_W


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
        (0.3, 1.7, 2.2, 1.6, "1. 類似 Top-K\n（前回 3-1）", "#6FA8D6"),
        (2.9, 1.7, 2.2, 1.6, "2. 類似群の\nCAR を集計", "#2E86AB"),
        (5.5, 1.7, 2.2, 1.6, "3. 群れの\nふつうの反応\n（近傍平均）", "#E26A2C"),
        (8.1, 1.7, 2.2, 1.6, "4. 自身の\n実績 CAR\nと比較", "#A23B72"),
        (10.7, 1.7, 2.0, 1.6, "5. 外れ大\n→ 個別\nショック", "#48A14D"),
    ]
    for x, y, w, h, t, c in steps:
        _box(ax, x, y, w, h, t, color=c, fontsize=20)
    for i in range(len(steps) - 1):
        x1 = steps[i][0] + steps[i][2]; x2 = steps[i + 1][0]
        _arrow(ax, x1, 2.5, x2, 2.5)

    ax.text(6.5, 4.75, "K-NN で「似た決算群から外れた銘柄＝個別ショック」を仕分ける",
            ha="center", fontsize=24, weight="bold")
    ax.text(6.5, 0.85, "値・方向そのものは予測できない（r ≈ 0）。だから当てにいかず、似た決算群から外れた銘柄を抽出する",
            ha="center", fontsize=18, color="#555", style="italic")
    ax.text(6.5, 0.30, "「当てる」ではなく「外れを拾う」 ― 機械学習の使いどころを見極める",
            ha="center", fontsize=16, color="#666")
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "01_pipeline.png")
    plt.close(fig)
    print("saved 01_pipeline.png")


def image_02_pred_vs_actual():
    """予測 CAR vs 実績 CAR 散布図（K=15, [-1,+5]）"""
    df = pd.read_csv(B16 / "predictions.csv")
    pred = df["pred_K15_p5"]
    actual = df["car_m1_p5"]

    fig, ax = plt.subplots(figsize=(FIG_W, 8))
    ax.scatter(pred, actual, s=22, alpha=0.55, color="#2E86AB", label=f"全 {len(df)} 銘柄")

    # 完璧予測ライン y=x
    lim = max(abs(pred).max(), abs(actual).max(), 30)
    ax.plot([-lim, lim], [-lim, lim], color="red", ls="--", lw=1.2, label="完璧予測 y=x", alpha=0.7)
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5)

    # 個別ショック銘柄（誤差 |10pp| 以上）を強調
    big_err = df[df["err_K15_p5"].abs() >= 10]
    ax.scatter(big_err["pred_K15_p5"], big_err["car_m1_p5"], s=80, marker="o",
               edgecolor="#A23B72", facecolor="none", lw=1.5,
               label=f"|誤差| >= 10pp ({len(big_err)} 銘柄, 個別ショック)", zorder=4)

    # narrative 5 強調
    n5 = df[df["code"].astype(str).isin(["8002", "2768"])]
    for _, r in n5.iterrows():
        ax.scatter(r["pred_K15_p5"], r["car_m1_p5"], s=250, marker="*",
                   edgecolor="black", facecolor="gold", lw=1.5, zorder=5)
        ax.annotate(r["company"][:6], (r["pred_K15_p5"], r["car_m1_p5"]),
                    xytext=(8, 8), textcoords="offset points", fontsize=12, weight="bold")

    corr = pred.corr(actual)
    rmse = np.sqrt(((actual - pred) ** 2).mean())
    dir_match = ((actual > 0) == (pred > 0)).mean() * 100

    ax.set_xlabel("予測 CAR[-1,+5]（類似 Top-15 平均、%）")
    ax.set_ylabel("実績 CAR[-1,+5]（%）")
    ax.set_title(f"K-NN 予測 (K=15) vs 実績 ― 相関 r = {corr:+.3f}, RMSE = {rmse:.2f}%, 方向一致 {dir_match:.1f}%",
                 pad=40)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.legend(loc="upper left", framealpha=0.95)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "02_pred_vs_actual.png")
    plt.close(fig)
    print("saved 02_pred_vs_actual.png")


def image_03_shocks_table():
    """個別ショック Top-15 を可視化（ポジ・ネガ並列）"""
    df = pd.read_csv(B16 / "predictions.csv")
    df["company"] = (df["company"].astype(str)
                     .str.replace("株式会社", "", regex=False).str.strip().str[:11])
    pos = df.nlargest(10, "err_K15_p5").copy()
    neg = df.nsmallest(10, "err_K15_p5").copy()

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 7))
    for ax, sub, title, color in [
        (axes[0], pos, "ポジティブショック Top-10（市場が想定より好評価）", "#48A14D"),
        (axes[1], neg, "ネガティブショック Top-10（市場が想定より悪評価）", "#A23B72"),
    ]:
        sub = sub.reset_index(drop=True)
        x = np.arange(len(sub))
        ax.barh(x - 0.20, sub["pred_K15_p5"], height=0.40, color="#C0C0C0", label="近傍平均（似たTop-15）")
        ax.barh(x + 0.20, sub["car_m1_p5"], height=0.40, color=color, label="実績")
        ax.axvline(0, color="black", lw=0.6)
        ax.set_yticks(x)
        ax.set_yticklabels([f"{r['code']} {r['company']}" for _, r in sub.iterrows()], fontsize=13)
        ax.set_xlabel("CAR[-1,+5]（%）")
        ax.set_title(title, pad=40, fontsize=16)
        # 凡例は軸内に置くと下段のバー・注釈を覆うため、パネル上端の外（タイトル下）へ
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncols=2,
                  fontsize=14, frameon=False)
        ax.grid(axis="x", alpha=0.3)
        ax.invert_yaxis()
        # 数値ラベルは常にバーと反対側の空き領域（パネル内の固定列）に置く。
        # バー先端に付けると、ネガ側で軸外にはみ出して銘柄名と重なるため。
        positive_panel = (sub["car_m1_p5"] >= 0).mean() >= 0.5
        lo, hi = ax.get_xlim()
        rng = hi - lo
        if positive_panel:
            ax.set_xlim(lo - 0.52 * rng, hi + 0.02 * rng)
            lo, hi = ax.get_xlim()
            label_x, label_ha = lo + 0.01 * (hi - lo), "left"
        else:
            ax.set_xlim(lo - 0.02 * rng, hi + 0.52 * rng)
            lo, hi = ax.get_xlim()
            label_x, label_ha = hi - 0.01 * (hi - lo), "right"
        for i, (a, e) in enumerate(zip(sub["car_m1_p5"], sub["err_K15_p5"])):
            ax.text(label_x, i + 0.20, f"{a:+.1f}%（外れ{e:+.1f}pp）",
                    va="center", fontsize=12, color=color, weight="bold",
                    ha=label_ha, zorder=5)

    fig.suptitle("個別ショック ― 似た決算群（近傍）の反応から大きく外れた銘柄",
                 y=0.96)
    fig.tight_layout()
    fig.subplots_adjust(top=0.75)
    bs.savefig_uniform(fig, OUT_DIR / "03_shocks_top10.png")
    plt.close(fig)
    print("saved 03_shocks_top10.png")


def image_05_strategy_flow():
    """16連載の到達点としてのハイブリッド戦略フロー"""
    fig, ax = plt.subplots(figsize=(FIG_W, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.text(6.5, 6.6, "全16連載の到達点 ― ハイブリッド投資ワークフロー",
            ha="center", fontsize=14, weight="bold")

    # Top row - data sources (フェーズ1-2)
    _box(ax, 0.3, 4.8, 3.0, 0.9, "市販指標\n(連載01-05)", color="#6FA8D6", fontsize=10)
    _box(ax, 3.6, 4.8, 3.0, 0.9, "XBRL→JSON\n(連載06-08)", color="#2E86AB", fontsize=10)
    _box(ax, 6.9, 4.8, 3.0, 0.9, "CAR×市場反応\n(連載13)", color="#E26A2C", fontsize=10)
    _box(ax, 10.2, 4.8, 2.5, 0.9, "LLM要約\n(連載14)", color="#A23B72", fontsize=10)

    # Middle row - analysis layers (フェーズ3)
    _box(ax, 0.3, 3.3, 4.0, 0.9, "進捗率Z / アクルーアル\n三角検証 / セグメント\n(連載09-12)",
         color="#48A14D", fontsize=10)
    _box(ax, 4.6, 3.3, 4.0, 0.9, "類似決算検索\n(連載15)", color="#48A14D", fontsize=10)
    _box(ax, 8.9, 3.3, 3.8, 0.9, "K-NN 分類 ― 個別ショック\n(連載16)", color="#48A14D", fontsize=10)

    # Arrows
    for x1, x2 in [(1.8, 1.8), (5.1, 5.1), (8.4, 8.4), (11.4, 10.8)]:
        _arrow(ax, x1, 4.8, x2, 4.2)

    # Bottom row - decisions
    _box(ax, 0.3, 1.6, 4.0, 1.0, "[BUY] 買い候補\n類似群+健全 × CAR上昇\n個別ポジショック",
         color="#48A14D", fontsize=11)
    _box(ax, 4.6, 1.6, 4.0, 1.0, "[WATCH] 要警戒\n類似群と乖離 × 個別ショック\n説明会IRを優先確認",
         color="#E26A2C", fontsize=11)
    _box(ax, 8.9, 1.6, 3.8, 1.0, "[SELL] 売り検討\n質低下シグナル × CAR下落\n個別ネガショック",
         color="#A23B72", fontsize=11)

    # 連載16 への矢印
    _arrow(ax, 2.3, 3.3, 2.3, 2.6)
    _arrow(ax, 6.6, 3.3, 6.6, 2.6)
    _arrow(ax, 10.8, 3.3, 10.8, 2.6)

    ax.text(6.5, 0.7, "個別投資家でも年間数千円〜数万円で運用可能。AI は予測ではなく「発見」のツール",
            ha="center", fontsize=11, color="#555", style="italic")
    ax.text(6.5, 0.2, "全16連載の到達点：構造化データ × 統計 × LLM × CAR 検証 の四位一体",
            ha="center", fontsize=10, color="#666")

    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "05_strategy_flow.png")
    plt.close(fig)
    print("saved 05_strategy_flow.png")


def main():
    image_01_pipeline()
    image_03_shocks_table()
    print(f"\nAll saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
