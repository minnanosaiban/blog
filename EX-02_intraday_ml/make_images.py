"""
blog/posts/17_intraday_ml.md 用の画像生成スクリプト。

生成画像:
  01_decile_returns.png — 確信度十分位 × 次バー平均リターン（単調な階段）
  02_edge_vs_cost.png   — L/S エッジ vs 往復コスト

数値の出典: data/blog21/results_summary.json（blog21_scalping_ml.py の出力）
実行: python scripts/blog/17_intraday_ml_make_images.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import numpy as np
import matplotlib.pyplot as plt
import _blog_style as bs

bs.apply_rcparams()
FIG_W = bs.FIG_W

C_UP = "#5a9a72"
C_DOWN = "#c87878"
C_NS = "#3498db"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"
C_COST = "#b8860b"

RES = json.loads(Path(r"C:\stock_analysis\data\blog21\results_summary.json")
                 .read_text(encoding="utf-8"))
OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/17_intraday_ml")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 1) 確信度十分位 × 次バー平均リターン ────────────────────────────────────
def make_decile_returns() -> None:
    dec = RES["decile_table"]
    keys = sorted(dec.keys(), key=int)
    vals = [dec[k]["mean_bps"] for k in keys]
    colors = [C_DOWN if v < 0 else C_UP for v in vals]

    fig, ax = plt.subplots(figsize=(FIG_W, 5.8))
    fig.subplots_adjust(top=0.80, bottom=0.18, left=0.09, right=0.97)
    x = np.arange(len(vals))
    ax.bar(x, vals, width=0.62, color=colors, alpha=0.9,
           edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, vals):
        ax.text(xi, v + (0.04 if v >= 0 else -0.08), f"{v:+.2f}",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=14, fontweight="bold",
                color=C_DOWN if v < 0 else C_UP)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(k) + 1}" for k in keys], fontsize=15)
    ax.set_xlabel("モデル確信度（上がる確率）の十分位  ―  1 = 最も下がる予想 / 10 = 最も上がる予想",
                  fontsize=15, color=C_TEXT_SUB)
    ax.set_ylabel("次バー平均リターン（bps）", fontsize=16, color=C_TEXT_SUB)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    auc = RES["auc_out"]
    ax.text(0.99, 0.04, f"OUT 51 万バー ・ AUC {auc:.3f}（ほぼコイン）",
            transform=ax.transAxes, fontsize=15, color=C_TEXT_SUB, ha="right")
    ax.set_title("確信度十分位 × 次バーリターン  ―  当てられないのに並べ替えはできている",
                 fontsize=21, fontweight="bold", color=C_TEXT, pad=30, loc="left")
    bs.savefig_uniform(fig, OUT_DIR / "01_decile_returns.png")
    plt.close(fig)


# ── 2) L/S エッジ vs コスト ─────────────────────────────────────────────────
def make_edge_vs_cost() -> None:
    items = [
        ("確信度トップ 10%\n→ 買い", RES["decile_top_long_bps"]),
        ("確信度ボトム 10%\n→ 売り", RES["decile_bottom_short_bps"]),
        ("ロング・ショート\n平均", RES["long_short_avg_bps"]),
    ]
    labels = [t for t, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(FIG_W, 5.8))
    fig.subplots_adjust(top=0.82, bottom=0.18, left=0.09, right=0.97)
    x = np.arange(len(vals))
    ax.bar(x, vals, width=0.5, color=C_NS, alpha=0.9,
           edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.12, f"+{v:.2f}", ha="center", fontsize=17,
                fontweight="bold", color=C_NS)
    ax.axhspan(5, 10, color=C_COST, alpha=0.12)
    ax.axhline(5, color=C_COST, linewidth=1.6, linestyle="--")
    ax.axhline(10, color=C_COST, linewidth=1.6, linestyle="--")
    ax.text(len(vals) - 0.55, 7.2, "往復コスト 5〜10bps の壁", fontsize=17,
            fontweight="bold", color=C_COST, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=15)
    ax.set_ylabel("OUT 1 回あたりエッジ（bps）", fontsize=16, color=C_TEXT_SUB)
    ax.set_ylim(0, 11.5)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("LightGBM のエッジはコストの 1/11  ―  並べ替えの両端を取引しても届かない",
                 fontsize=21, fontweight="bold", color=C_TEXT, pad=30, loc="left")
    bs.savefig_uniform(fig, OUT_DIR / "02_edge_vs_cost.png")
    plt.close(fig)


if __name__ == "__main__":
    make_decile_returns()
    print("[ok] 01_decile_returns.png")
    make_edge_vs_cost()
    print("[ok] 02_edge_vs_cost.png")
