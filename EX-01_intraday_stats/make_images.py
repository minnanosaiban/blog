"""
blog/posts/16_intraday_stats.md 用の画像生成スクリプト。

生成画像:
  01_signal_inout.png   — 定番シグナル 3 本の IN/OUT 比較（時間帯・ギャップ・リードラグ）
  02_meanrev_vs_cost.png — 平均回帰系のエッジ vs 往復コスト
  03_event_drift.png    — 場中開示後 30 分のドリフト（変動倍率と初動追随戦略）

数値の出典: data/blog20/（blog20_scalping_stats.py / blog20b_conditional_patterns.py の出力）
実行: python scripts/blog/16_intraday_stats_make_images.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import numpy as np
import pandas as pd
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

DATA = Path(r"C:\stock_analysis\data\blog20")
OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/16_intraday_stats")
OUT_DIR.mkdir(parents=True, exist_ok=True)

RES = json.loads((DATA / "results_summary.json").read_text(encoding="utf-8"))
COND = json.loads((DATA / "conditional_patterns.json").read_text(encoding="utf-8"))


# ── 1) 定番シグナル 3 本の IN/OUT 比較 ──────────────────────────────────────
def make_signal_inout() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(FIG_W, 5.6),
                             gridspec_kw=dict(wspace=0.42))
    fig.subplots_adjust(top=0.74, bottom=0.16, left=0.07, right=0.985)

    # (a) 時間帯の癖: IN vs OUT 散布
    tbl = pd.read_parquet(DATA / "exp1_seasonality.parquet").dropna()
    ax = axes[0]
    ax.scatter(tbl["in_bps"], tbl["out_bps"], s=42, color=C_NS, alpha=0.65,
               edgecolor="white", linewidth=0.6)
    lim = max(abs(tbl["in_bps"]).max(), abs(tbl["out_bps"]).max()) * 1.15
    ax.axhline(0, color="#999999", linewidth=0.7)
    ax.axvline(0, color="#999999", linewidth=0.7)
    ax.plot([-lim, lim], [-lim, lim], color="#bbbbbb", linewidth=0.8, linestyle="--")
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_xlabel("IN 平均（bps）", fontsize=15, color=C_TEXT_SUB)
    ax.set_ylabel("OUT 平均（bps）", fontsize=15, color=C_TEXT_SUB)
    corr = RES["exp1_seasonality"]["in_out_corr"]
    ax.text(0.04, 0.93, f"相関 {corr:.3f}", transform=ax.transAxes,
            fontsize=16, fontweight="bold", color=C_DOWN)
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("時間帯の癖（65 バー）\n前半 vs 後半", fontsize=16,
                 fontweight="bold", color=C_TEXT, pad=14, loc="left")

    # (b) ギャップ十分位 → 寄り後 30 分
    dec = pd.read_parquet(DATA / "exp2_gap_deciles.parquet")
    ax = axes[1]
    x = np.arange(len(dec))
    ax.plot(x, dec[("in", "r30")], "o-", color="#888888", linewidth=2,
            markersize=7, label="IN（前半）")
    ax.plot(x, dec[("out", "r30")], "o-", color=C_NS, linewidth=2,
            markersize=7, label="OUT（後半）")
    ax.axhline(0, color="#999999", linewidth=0.7)
    ax.set_xlabel("寄りギャップ 十分位（小→大）", fontsize=15, color=C_TEXT_SUB)
    ax.set_ylabel("寄り後 30 分（bps）", fontsize=15, color=C_TEXT_SUB)
    ax.legend(fontsize=14, frameon=True, facecolor="white", edgecolor="#dddddd")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("寄りギャップ → 30 分\n前半と後半で形が変わる", fontsize=16,
                 fontweight="bold", color=C_TEXT, pad=14, loc="left")

    # (c) リードラグ上位 3 ペア: IN 相関は正でも OUT はマイナス
    ax = axes[2]
    checks = RES["exp4_leadlag"]["top3_out_check"]
    short = {"出光興産": "出光", "コスモエネＨＤ": "コスモ", "三井物産": "三井物",
             "豊田通商": "豊田通", "双日": "双日"}
    names = []
    for c in checks:
        a, b = c["pair"].split("→")
        names.append(f"{short.get(a, a)}→{short.get(b, b)}")
    outv = [c["out_per_trade_bps"] for c in checks]
    y = np.arange(len(checks))[::-1]
    ax.barh(y, outv, color=C_DOWN, alpha=0.9, height=0.55,
            edgecolor="white", linewidth=0.8)
    xmin = min(outv) * 1.6
    for yi, c, v in zip(y, checks, outv):
        ax.text(v - abs(xmin) * 0.03, yi, f"{v:+.2f}", va="center", ha="right",
                fontsize=14, color=C_DOWN, fontweight="bold")
    ax.text(0.97, 0.93, f"IN 相関は +0.03〜+{checks[0]['corr_in']:.3f}",
            transform=ax.transAxes, fontsize=14, color=C_TEXT_SUB, ha="right")
    ax.axvline(0, color="#999999", linewidth=0.7)
    ax.set_xlim(xmin, 0.05)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=14)
    ax.set_xlabel("OUT 1 回あたり（bps・コスト前）", fontsize=15, color=C_TEXT_SUB)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("リードラグ上位 3 ペア\nIN で選び OUT で検証", fontsize=16,
                 fontweight="bold", color=C_TEXT, pad=14, loc="left")

    fig.suptitle("定番シグナル 3 本の IN/OUT 比較  ―  前半で見えた癖は後半に残らない",
                 fontsize=22, fontweight="bold", color=C_TEXT, y=0.97)
    bs.savefig_uniform(fig, OUT_DIR / "01_signal_inout.png")
    plt.close(fig)


# ── 2) 平均回帰系のエッジ vs コスト ─────────────────────────────────────────
def make_meanrev_vs_cost() -> None:
    mr = RES["exp3_momentum_mr"]["out_sample"]
    sA = COND["expA_streak_reversal"]
    items = [
        ("平均回帰\n（直前 5 分の逆張り）", abs(mr["k=1"]["edge_bps_momentum"])),
        ("2 連続上昇\n→ 売り", sA["2連続up → 逆張り"]["out"]["per_trade_bps"]),
        ("4 連続上昇\n→ 売り", sA["4連続up → 逆張り"]["out"]["per_trade_bps"]),
        ("6 連続上昇\n→ 売り", sA["6連続up → 逆張り"]["out"]["per_trade_bps"]),
    ]
    labels = [t for t, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(FIG_W, 5.8))
    fig.subplots_adjust(top=0.82, bottom=0.18, left=0.09, right=0.97)
    x = np.arange(len(vals))
    ax.bar(x, vals, width=0.52, color=C_NS, alpha=0.9,
           edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.12, f"+{v:.2f}", ha="center", fontsize=16,
                fontweight="bold", color=C_NS)
    # コスト帯
    ax.axhspan(5, 10, color=C_COST, alpha=0.12)
    ax.axhline(5, color=C_COST, linewidth=1.6, linestyle="--")
    ax.axhline(10, color=C_COST, linewidth=1.6, linestyle="--")
    ax.text(len(vals) - 0.45, 7.2, "往復コスト 5〜10bps の壁", fontsize=17,
            fontweight="bold", color=C_COST, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=15)
    ax.set_ylabel("OUT 1 回あたりエッジ（bps）", fontsize=16, color=C_TEXT_SUB)
    ax.set_ylim(0, 11.5)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("平均回帰のエッジはコストの壁に届かない  ―  条件を極端にしても 1bps 未満",
                 fontsize=21, fontweight="bold", color=C_TEXT, pad=30, loc="left")
    bs.savefig_uniform(fig, OUT_DIR / "02_meanrev_vs_cost.png")
    plt.close(fig)


# ── 3) 場中開示後 30 分のドリフト ───────────────────────────────────────────
def make_event_drift() -> None:
    dd = pd.read_parquet(DATA / "exp5_event_drift.parquet")
    e5 = RES["exp5_event_drift"]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(FIG_W, 5.8),
                                     gridspec_kw=dict(wspace=0.42))
    fig.subplots_adjust(top=0.76, bottom=0.16, left=0.09, right=0.975)

    # 左: 開示後 30 分の変動（絶対値の中央値）比較
    cats = ["通常時\n（全バー）", "その他開示\n後 30 分", "決算系開示\n後 30 分"]
    vals = [e5["baseline_median_abs30_bps"],
            e5["その他開示"]["median_abs30_bps"],
            e5["決算系"]["median_abs30_bps"]]
    colors = ["#aaaaaa", C_NS, C_DOWN]
    x = np.arange(len(vals))
    ax_l.bar(x, vals, width=0.5, color=colors, alpha=0.9,
             edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, vals):
        ax_l.text(xi, v + 3, f"{v:.0f}", ha="center", fontsize=17,
                  fontweight="bold", color=C_TEXT)
    ax_l.text(2, vals[2] + 22, f"約 {vals[2] / vals[0]:.0f} 倍", ha="center",
              fontsize=18, fontweight="bold", color=C_DOWN)
    ax_l.set_xticks(x)
    ax_l.set_xticklabels(cats, fontsize=15)
    ax_l.set_ylabel("30 分の変動・絶対値の中央値（bps）", fontsize=15, color=C_TEXT_SUB)
    ax_l.set_ylim(0, vals[2] * 1.35)
    ax_l.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("場中開示の直後だけ値が動く", fontsize=17,
                   fontweight="bold", color=C_TEXT, pad=20, loc="left")

    # 右: 初動追随戦略の平均パス（決算系）
    k = dd[dd.is_kessan]
    sgn = np.sign(k["t+1"])
    path = [float((sgn * (k[f"t+{i}"] - k["t+1"])).mean()) * 1e4 for i in range(1, 7)]
    xs = np.arange(1, 7) * 5  # 分
    ax_r.plot(xs, path, "o-", color=C_UP, linewidth=2.5, markersize=8)
    ax_r.fill_between(xs, 0, path, color=C_UP, alpha=0.12)
    ax_r.axhspan(5, 10, color=C_COST, alpha=0.12)
    ax_r.axhline(5, color=C_COST, linewidth=1.4, linestyle="--")
    ax_r.axhline(10, color=C_COST, linewidth=1.4, linestyle="--")
    ax_r.text(29.5, 7.0, "コスト 5〜10bps", fontsize=14, color=C_COST,
              ha="right", fontweight="bold")
    ax_r.text(xs[-1], path[-1] + 1.2, f"+{path[-1]:.0f}bps", fontsize=18,
              fontweight="bold", color=C_UP, ha="right")
    ax_r.set_xlabel("開示後の経過（分）", fontsize=15, color=C_TEXT_SUB)
    ax_r.set_ylabel("初動 5 分に追随した平均損益（bps）", fontsize=15, color=C_TEXT_SUB)
    ax_r.set_xticks(xs)
    ax_r.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title(f"初動の方向に乗る（決算系 {len(k)} 件）", fontsize=17,
                   fontweight="bold", color=C_TEXT, pad=20, loc="left")

    fig.suptitle("場中開示後 30 分のドリフト  ―  唯一コスト控除後も残ったシグナル",
                 fontsize=22, fontweight="bold", color=C_TEXT, y=0.965)
    bs.savefig_uniform(fig, OUT_DIR / "03_event_drift.png")
    plt.close(fig)


if __name__ == "__main__":
    make_signal_inout()
    print("[ok] 01_signal_inout.png")
    make_meanrev_vs_cost()
    print("[ok] 02_meanrev_vs_cost.png")
    make_event_drift()
    print("[ok] 03_event_drift.png")
