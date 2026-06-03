"""
連載 3-4 ランダムフォレスト ― 画像生成スクリプト
入力: data/blog18/{importance,accuracy}.csv
出力: docs/blog/posts/img/13_random_forest/
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
B18 = ROOT / "data" / "blog18"
OUT_DIR = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/13_random_forest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

bs.apply_rcparams()
FIG_W = bs.FIG_W

JP = {
    "net_sales_yoy": "売上YoY", "operating_yoy": "営利YoY", "pretax_yoy": "税引前YoY",
    "net_income_yoy": "純利YoY", "comprehensive_yoy": "包括YoY", "div_growth_pct": "配当成長",
    "op_margin": "営業利益率", "net_margin": "純利益率", "segment_count": "ｾｸﾞﾒﾝﾄ数",
    "max_seg_share": "主力依存度",
}


def image_01_accuracy():
    acc = pd.read_csv(B18 / "accuracy.csv").iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 5))

    ax = axes[0]
    names = ["多数派\nベースライン", "RF\n(CV 5-fold)", "RF\n(test 30%)"]
    vals = [acc["baseline_acc"], acc["cv_acc"], acc["test_acc"]]
    colors = ["#9aa0a6", "#A23B72", "#C98AB0"]
    bars = ax.bar(names, vals, color=colors, width=0.6)
    ax.axhline(acc["baseline_acc"], color="#9aa0a6", ls="--", lw=1.3)
    ax.set_ylim(0.45, 0.65)
    ax.set_ylabel("正解率（CAR の上 / 下 を当てる）")
    ax.set_title("予測精度 ― RF は多数派ベースラインを超えない", pad=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.004, f"{v:.3f}",
                ha="center", fontsize=12, weight="bold")

    ax = axes[1]
    names2 = ["RF (CV)", "RF (test)"]
    aucs = [acc["cv_auc"], acc["test_auc"]]
    bars = ax.bar(names2, aucs, color="#2E86AB", width=0.5)
    ax.axhline(0.5, color="red", ls="--", lw=1.3, label="ランダム (AUC 0.5)")
    ax.set_ylim(0.45, 0.65)
    ax.set_ylabel("AUC")
    ax.set_title("AUC ― ランダム(0.5)にほぼ等しい", pad=12)
    for b, v in zip(bars, aucs):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.004, f"{v:.3f}",
                ha="center", fontsize=12, weight="bold")
    ax.legend(loc="upper right")

    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "01_accuracy.png")
    plt.close(fig)
    print("saved 01_accuracy.png")


def image_02_importance():
    imp = pd.read_csv(B18 / "importance.csv")
    imp = imp.sort_values("impurity", ascending=True).reset_index(drop=True)  # for barh (bottom=low)
    labels = [JP[f] for f in imp["feature"]]
    yy = np.arange(len(imp))

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 6), sharey=True)

    ax = axes[0]
    ax.barh(yy, imp["impurity"], color="#2E86AB", height=0.65)
    ax.set_yticks(yy)
    ax.set_yticklabels(labels)
    ax.set_xlabel("重要度（不純度ベース・合計1）")
    ax.set_title("impurity 重要度 ― 「効く」ように見える", pad=12)
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(imp["impurity"]):
        ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=10)

    ax = axes[1]
    colors = ["#48A14D" if v > 0 else "#C0504D" for v in imp["perm_mean"]]
    ax.barh(yy, imp["perm_mean"], xerr=imp["perm_std"], color=colors, height=0.65,
            error_kw=dict(ecolor="#888", lw=1))
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("重要度（permutation・精度の低下幅）")
    ax.set_title("permutation 重要度（実測）― ほぼ 0", pad=12)
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    bs.savefig_uniform(fig, OUT_DIR / "02_importance.png")
    plt.close(fig)
    print("saved 02_importance.png")


def main():
    image_01_accuracy()
    image_02_importance()
    print(f"\nAll saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
