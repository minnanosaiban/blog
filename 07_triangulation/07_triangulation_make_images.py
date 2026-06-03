"""
blog/11_予想検証.md 用の画像生成スクリプト。

生成画像:
  01_triangulation_concept.png — 3 ソース×3 ペア比較の概念図
  02_quadrant_scatter.png      — ガイダンスvs業績 × コンセンサスvsガイダンス 4 象限散布図
  03_upside_top10.png          — 上方修正期待 Top10（保守ガイダンス×アナリスト強気）
  04_downside_top10.png        — 達成困難 Top10（強気ガイダンス×アナリスト懐疑）
  05_trading_companies.png     — 総合商社 8 社の予想検証 × アクルーアル接続

実行: python scripts/blog/10_triangulation_make_images.py
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import _blog_style as bs
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── デザイン設定 ────────────────────────────────────────────────────────────
bs.apply_rcparams()
FIG_W = bs.FIG_W

C_ACT  = "#444444"  # 業績
C_GUI  = "#777777"  # ガイダンス
C_CONS = "#aaaaaa"  # コンセンサス
C_UP   = "#5a9a72"  # 上方修正期待
C_WARN = "#c87878"  # 達成困難
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/07_triangulation")
OUT_DIR.mkdir(parents=True, exist_ok=True)


_savefig_vpad = bs.savefig_uniform   # 横幅も統一して保存（共通モジュール）


STMTS = Path(r"C:/stock_analysis/data/statements")


def _to_float(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    if s in ("", "-", "－", "---"):
        return None
    try:
        return float(s.replace(",", "").replace("+", ""))
    except ValueError:
        return None


def load_triangulation() -> pd.DataFrame:
    """3 ソース統合: 決算短信 actual + 決算短信 forecast + rakunav 213 EPS(予)"""
    rows = []
    for f in STMTS.glob("*_FY.json"):
        parts = f.stem.split("_")
        code = parts[0]
        fy_end = parts[1] if len(parts) > 1 else ""
        is_forecast = "forecast" in f.name
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {})
        perf = d.get("performance", {}).get("current") or {}
        rows.append({
            "code": code,
            "name": meta.get("company_name", ""),
            "fy_end": fy_end,
            "is_forecast": is_forecast,
            "eps": perf.get("eps"),
            "net_income": perf.get("net_income"),
            "net_sales": perf.get("net_sales"),
            "op_income": perf.get("operating_income"),
        })
    df = pd.DataFrame(rows)

    actual = df[~df["is_forecast"]].sort_values("fy_end").groupby("code").tail(1)
    forecast = df[df["is_forecast"]].sort_values("fy_end").groupby("code").tail(1)

    m = actual.merge(forecast, on="code", suffixes=("_a", "_f"))

    # rakunav 213 EPS(予)
    rk = pd.read_csv(rakunav_file(213), encoding="utf-8-sig", dtype=str)
    rk["コード"] = rk["コード"].str.strip()
    val_col = [c for c in rk.columns
               if "EPS" in c and c not in ["コード", "銘柄名", "市場"]][0]
    rk["eps_consensus"] = rk[val_col].map(_to_float)

    m = m.merge(rk[["コード", "eps_consensus"]].rename(columns={"コード": "code"}),
                on="code", how="left")
    m = m.dropna(subset=["eps_a", "eps_f", "eps_consensus"])
    m = m[(m["eps_a"].abs() > 1) & (m["eps_f"].abs() > 1) & (m["eps_consensus"].abs() > 1)]

    m["guide_vs_actual_pct"] = (m["eps_f"] - m["eps_a"]) / m["eps_a"].abs() * 100
    m["consensus_vs_guide_pct"] = (m["eps_consensus"] - m["eps_f"]) / m["eps_f"].abs() * 100
    m["consensus_vs_actual_pct"] = (m["eps_consensus"] - m["eps_a"]) / m["eps_a"].abs() * 100

    m = apply_master_names(m, code_col="code", name_col="name_a")
    return m


# ── 1) 予想検証の概念図 ────────────────────────────────────────────────────
def make_concept() -> None:
    fig, ax = plt.subplots(figsize=(FIG_W, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9.6)
    ax.axis("off")

    # 3 頂点（業績=頂点・ガイダンス=左下・コンセンサス=右下：サムネイルと同配置）
    nodes = {
        "actual":    (6.0, 7.3, C_ACT,  "業績", "会社の確定業績"),
        "guidance":  (2.3, 2.2, C_GUI,  "ガイダンス", "会社の来期予想"),
        "consensus": (9.7, 2.2, C_CONS, "コンセンサス", "アナリスト平均予想"),
    }
    for key, (x, y, color, label, sub) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - 1.7, y - 0.7), 3.4, 1.4,
                                    boxstyle="round,pad=0.08",
                                    linewidth=2.4, edgecolor=color,
                                    facecolor="white"))
        ax.text(x, y + 0.18, label, ha="center", va="center",
                fontsize=19, fontweight="bold", color=color)
        ax.text(x, y - 0.42, sub, ha="center", va="center",
                fontsize=14, color=C_TEXT_SUB)

    a, g, c = nodes["actual"], nodes["guidance"], nodes["consensus"]
    # 3 辺（ペア比較）
    edges = [
        (a, g, "ガイダンス − 業績\n＋ 強気 / − 保守", -1.0),
        (a, c, "コンセンサス − 業績\n来期の成長期待", 1.0),
        (g, c, "コンセンサス − ガイダンス\n＋ アナリスト強気", 0.0),
    ]
    for n1, n2, label, dx in edges:
        ax.add_patch(FancyArrowPatch((n1[0], n1[1]), (n2[0], n2[1]),
                     arrowstyle="<->", mutation_scale=20,
                     color="#bbbbbb", linewidth=1.6, shrinkA=46, shrinkB=46))
        mx, my = (n1[0] + n2[0]) / 2 + dx, (n1[1] + n2[1]) / 2
        ax.text(mx, my, label, fontsize=15, ha="center", va="center",
                color="#444444", fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="#cccccc",
                          boxstyle="round,pad=0.3"))

    ax.text(6.0, 8.9, "予想検証  ―  3 ソースを三角形で比較",
            fontsize=20, fontweight="bold", color=C_TEXT, ha="center", va="center")
    ax.text(6.0, 0.5,
            "保守ガイダンス × アナリスト強気 → 上方修正期待大\n"
            "強気ガイダンス × アナリスト懐疑 → 達成困難",
            fontsize=15, ha="center", va="center", color=C_TEXT_SUB, style="italic")

    _savefig_vpad(fig, OUT_DIR / "01_triangulation_concept.png")
    plt.close(fig)


# ── 2) 4 象限散布図 ────────────────────────────────────────────────────────
def make_quadrant_scatter(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(FIG_W, 8))

    sub = m[m["guide_vs_actual_pct"].between(-100, 100) &
            m["consensus_vs_guide_pct"].between(-50, 100)]

    # ゾーン背景
    ax.axhspan(0, 100, xmin=0, xmax=0.5, facecolor=C_UP, alpha=0.05)   # 左上
    ax.axhspan(-50, 0, xmin=0.5, xmax=1, facecolor=C_WARN, alpha=0.05)  # 右下

    # 通常銘柄
    bg = sub[((sub["guide_vs_actual_pct"] >= 0) | (sub["consensus_vs_guide_pct"] <= 5)) &
             ((sub["guide_vs_actual_pct"] <= 10) | (sub["consensus_vs_guide_pct"] >= -5))]
    ax.scatter(bg["guide_vs_actual_pct"], bg["consensus_vs_guide_pct"],
               s=25, color="#aaaaaa", alpha=0.5, edgecolors="white",
               linewidth=0.3)

    # 上方修正期待（左上）
    up = sub[(sub["guide_vs_actual_pct"] < 0) & (sub["consensus_vs_guide_pct"] > 5)]
    ax.scatter(up["guide_vs_actual_pct"], up["consensus_vs_guide_pct"],
               s=55, color=C_UP, alpha=0.85, edgecolors="white", linewidth=0.5,
               label=f"上方修正期待 ({len(up)})", zorder=4)

    # 達成困難（右下）
    dn = sub[(sub["guide_vs_actual_pct"] > 10) & (sub["consensus_vs_guide_pct"] < -5)]
    ax.scatter(dn["guide_vs_actual_pct"], dn["consensus_vs_guide_pct"],
               s=55, color=C_WARN, alpha=0.85, edgecolors="white", linewidth=0.5,
               label=f"達成困難 ({len(dn)})", zorder=4)

    # 主要銘柄ハイライト
    majors = [("7203", "トヨタ"), ("7974", "任天堂"), ("9432", "ＮＴＴ"),
              ("8053", "住友商事"), ("8001", "伊藤忠商事"), ("8058", "三菱商事"),
              ("8031", "三井物産"), ("6758", "ソニーＧ"), ("9433", "ＫＤＤＩ")]
    for code, label in majors:
        r = m.loc[m["code"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        x, y = r["guide_vs_actual_pct"], r["consensus_vs_guide_pct"]
        if not (-100 <= x <= 100 and -50 <= y <= 100):
            continue
        ax.scatter(x, y, s=180, color=C_TEXT, edgecolor="white",
                   linewidth=2.0, zorder=8, marker="*")
        ax.annotate(label, xy=(x, y), xytext=(8, 8),
                    textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    bbox=dict(facecolor="white", edgecolor="#aaaaaa",
                              boxstyle="round,pad=0.25"),
                    zorder=9)

    # 基準線
    ax.axhline(0, color="#777777", linewidth=0.8)
    ax.axvline(0, color="#777777", linewidth=0.8)

    # ゾーンラベル
    ax.text(-70, 70, "★上方修正期待大★\n保守ガイダンス\n× アナリスト強気",
            fontsize=16, fontweight="bold", color=C_UP,
            ha="center", va="center")
    ax.text(60, -30, "⚠ 達成困難 ⚠\n強気ガイダンス\n× アナリスト懐疑",
            fontsize=16, fontweight="bold", color=C_WARN,
            ha="center", va="center")
    ax.text(60, 70, "両者強気\n（過熱注意）", fontsize=16,
            color=C_TEXT_SUB, ha="center", va="center")
    ax.text(-70, -30, "両者弱気\n（業界全体不調）", fontsize=16,
            color=C_TEXT_SUB, ha="center", va="center")

    ax.set_xlim(-100, 100)
    ax.set_ylim(-50, 100)
    ax.set_xlabel("ガイダンス − 業績（%）  ← 保守     強気 →",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("コンセンサス − ガイダンス（%）  ← 懐疑    強気 →",
                  fontsize=16, color=C_TEXT)
    ax.set_title(f"予想検証 4 象限マップ  ―  決算短信 211 銘柄",
                 fontsize=20, fontweight="bold", color=C_TEXT,
                 pad=30, loc="left")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper right", fontsize=16, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    _savefig_vpad(fig, OUT_DIR / "02_quadrant_scatter.png")
    plt.close(fig)


# ── 3) 上方修正期待 Top10 ────────────────────────────────────────────────
def make_upside_top10(m: pd.DataFrame) -> None:
    sub = m[(m["guide_vs_actual_pct"] < 0) & (m["consensus_vs_guide_pct"] > 5)]
    sub = sub[sub["consensus_vs_guide_pct"] < 500]  # 極端値除外
    top = sub.nlargest(10, "consensus_vs_guide_pct").iloc[::-1]

    fig, ax = plt.subplots(figsize=(FIG_W, 7))
    y = np.arange(len(top))
    bw = 0.35

    ax.barh(y - bw / 2, top["guide_vs_actual_pct"], height=bw,
            color="#85c1e9", alpha=0.85, edgecolor="white", linewidth=0.8,
            label="ガイダンス − 業績（左軸）")
    ax.barh(y + bw / 2, top["consensus_vs_guide_pct"], height=bw,
            color=C_UP, alpha=0.85, edgecolor="white", linewidth=0.8,
            label="コンセンサス − ガイダンス（右軸）")

    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r["guide_vs_actual_pct"] - 2, i - bw / 2,
                f"{r['guide_vs_actual_pct']:+.1f}%",
                va="center", ha="right", fontsize=16,
                color="#3498db", fontweight="bold")
        ax.text(r["consensus_vs_guide_pct"] + 2, i + bw / 2,
                f"+{r['consensus_vs_guide_pct']:.1f}%",
                va="center", ha="left", fontsize=16,
                color=C_UP, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name_a'][:14]}"
                        for _, r in top.iterrows()], fontsize=16)
    ax.axvline(0, color="#444444", linewidth=0.8)
    ax.set_xlabel("乖離率（%）",
                  fontsize=16, color=C_TEXT_SUB)
    ax.set_xlim(top["guide_vs_actual_pct"].min() * 1.15,
                top["consensus_vs_guide_pct"].max() * 1.15)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "★ 上方修正期待 Top 10  ―  保守ガイダンス × アナリスト強気",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=40, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "03_upside_top10.png")
    plt.close(fig)


# ── 4) 達成困難 Top10 ────────────────────────────────────────────────
def make_downside_top10(m: pd.DataFrame) -> None:
    sub = m[(m["guide_vs_actual_pct"] > 10) & (m["consensus_vs_guide_pct"] < -5)]
    sub = sub[sub["guide_vs_actual_pct"] < 500]  # 極端値除外
    top = sub.nsmallest(10, "consensus_vs_guide_pct").iloc[::-1]

    fig, ax = plt.subplots(figsize=(FIG_W, 7))
    y = np.arange(len(top))
    bw = 0.35

    ax.barh(y - bw / 2, top["guide_vs_actual_pct"], height=bw,
            color="#f1c40f", alpha=0.85, edgecolor="white", linewidth=0.8,
            label="ガイダンス − 業績（強気プラス）")
    ax.barh(y + bw / 2, top["consensus_vs_guide_pct"], height=bw,
            color=C_WARN, alpha=0.85, edgecolor="white", linewidth=0.8,
            label="コンセンサス − ガイダンス（懐疑マイナス）")

    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r["guide_vs_actual_pct"] + 2, i - bw / 2,
                f"+{r['guide_vs_actual_pct']:.1f}%",
                va="center", ha="left", fontsize=16,
                color="#F39C12", fontweight="bold")
        ax.text(r["consensus_vs_guide_pct"] - 2, i + bw / 2,
                f"{r['consensus_vs_guide_pct']:.1f}%",
                va="center", ha="right", fontsize=16,
                color=C_WARN, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name_a'][:14]}"
                        for _, r in top.iterrows()], fontsize=16)
    ax.axvline(0, color="#444444", linewidth=0.8)
    ax.set_xlabel("乖離率（%）",
                  fontsize=16, color=C_TEXT_SUB)
    ax.legend(loc="upper right", fontsize=16, frameon=False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "⚠ 達成困難 Top 10  ―  強気ガイダンス × アナリスト懐疑",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=40, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "04_downside_top10.png")
    plt.close(fig)


# ── 5) 総合商社 8 社の予想検証 × 連載10 アクルーアル接続 ──────────────────
def make_trading_companies(m: pd.DataFrame) -> None:
    """総合商社 8 社の予想検証 + 連載10 で算出した平均アクルーアル比率を並べる。"""
    # 連載10 と共通の総合商社・エネルギー 8 社
    targets = [
        ("8053", "住友商事",   -0.0075),
        ("8001", "伊藤忠商事", -0.0150),
        ("8002", "丸紅",       -0.0168),
        ("8015", "豊田通商",   -0.0166),
        ("8020", "兼松",       -0.0154),
        ("8031", "三井物産",   -0.0041),
        ("8058", "三菱商事",   -0.0221),
        ("2768", "双日",       -0.0009),
    ]

    rows = []
    for code, label, accr in targets:
        r = m.loc[m["code"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append({
            "label": label, "code": code, "accrual": accr,
            "ga": r["guide_vs_actual_pct"],
            "cg": r["consensus_vs_guide_pct"],
        })
    rdf = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 7.8),
                             gridspec_kw=dict(width_ratios=[1.5, 1], wspace=0.26))
    fig.subplots_adjust(top=0.67, bottom=0.12, left=0.16, right=0.985)

    y = np.arange(len(rdf))
    bw = 0.38

    # ── 左: 予想検証バー（ガイダンス vs 業績、コンセンサス vs ガイダンス）──────
    # 住友商事の +311.6% が突出して他 7 社を潰すため、表示域を ±X_LIM にクリップし
    # 軸外に出る値は「▶ 値」で注記する（全社のバーを読める状態に保つ）。
    ax_l = axes[0]
    X_MIN, X_MAX = -90, 95
    C_GA, C_CG = "#5aa0d8", "#9aa0a6"          # ガイダンス−業績 / コンセンサス−ガイダンス
    C_GA_TXT, C_CG_TXT = "#1f6fb0", "#5f6368"  # 値ラベル（薄すぎず読める濃さ）

    ax_l.barh(y - bw / 2, rdf["ga"].clip(X_MIN, X_MAX), height=bw,
              color=C_GA, alpha=0.92, edgecolor="white", linewidth=0.8,
              label="ガイダンス − 業績（会社）")
    ax_l.barh(y + bw / 2, rdf["cg"].clip(X_MIN, X_MAX), height=bw,
              color=C_CG, alpha=0.92, edgecolor="white", linewidth=0.8,
              label="コンセンサス − ガイダンス（アナリスト）")

    def _bar_label(ax, val, ypos, color):
        """バー端に値を表示。軸外の値は端に寄せて ▶ / ◀ で注記。"""
        if val > X_MAX:
            ax.text(X_MAX - 2, ypos, f"{val:+.1f}% ▶", va="center", ha="right",
                    fontsize=17, color=color, fontweight="bold")
        elif val < X_MIN:
            ax.text(X_MIN + 2, ypos, f"◀ {val:+.1f}%", va="center", ha="left",
                    fontsize=17, color=color, fontweight="bold")
        else:
            ax.text(val + (1.6 if val >= 0 else -1.6), ypos, f"{val:+.1f}%",
                    va="center", ha="left" if val >= 0 else "right",
                    fontsize=17, color=color, fontweight="bold")

    for i, r in rdf.iterrows():
        _bar_label(ax_l, r["ga"], i - bw / 2, C_GA_TXT)
        _bar_label(ax_l, r["cg"], i + bw / 2, C_CG_TXT)

    ax_l.axvline(0, color="#444444", linewidth=1.0)
    ax_l.set_xlim(X_MIN, X_MAX)
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([f"{r['code']} {r['label']}" for _, r in rdf.iterrows()],
                         fontsize=19)
    ax_l.set_xlabel("乖離率（%）　　← 保守 / 懐疑　　　強気 →",
                    fontsize=18, color=C_TEXT)
    ax_l.tick_params(axis="x", labelsize=17)
    ax_l.legend(loc="center right", bbox_to_anchor=(0.995, 0.27),
                fontsize=14, frameon=True,
                facecolor="white", edgecolor="#dddddd")
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.6)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("予想検証（連載11）：業績予想の強気・保守",
                   fontsize=21, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    # ── 右: 連載10 のアクルーアル比率 ──────────────────────────────────
    ax_r = axes[1]
    colors = ["#5a9a72" if a < -0.01 else "#85c1e9" if a < 0 else "#F39C12"
              for a in rdf["accrual"]]
    ax_r.barh(y, rdf["accrual"], color=colors, alpha=0.92,
              edgecolor="white", linewidth=0.8, height=0.6)
    for i, r in rdf.iterrows():
        ax_r.text(r["accrual"] - 0.0013, i, f"{r['accrual']:+.4f}",
                  va="center", ha="right",
                  fontsize=16, color=C_TEXT, fontweight="bold")
    ax_r.axvline(0, color="#999999", linewidth=0.9)
    ax_r.set_yticks(y)
    ax_r.set_yticklabels([""] * len(rdf))
    ax_r.set_xlabel("7 年平均アクルーアル比率　　← 健全（利益の質 高い）",
                    fontsize=18, color=C_TEXT)
    ax_r.tick_params(axis="x", labelsize=17)
    ax_r.set_xlim(-0.05, 0.01)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.6)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("アクルーアル（連載10）：利益の質",
                   fontsize=21, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    fig.suptitle(
        "総合商社 8 社 ― 利益の質（アクルーアル）× 業績予想（予想検証）のクロス検証",
        fontsize=25, fontweight="bold", color=C_TEXT, y=0.985,
    )
    fig.text(0.5, 0.900,
             "8 社とも利益の質は健全。予想検証では住友商事だけが"
             "「保守ガイダンス × アナリスト強気（＝上方修正期待）」を維持",
             ha="center", va="center", fontsize=15, color=C_TEXT_SUB)

    _savefig_vpad(fig, OUT_DIR / "05_trading_companies.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    m = load_triangulation()
    print(f"[load] {len(m)} 銘柄で予想検証可能")

    make_concept()
    print("[ok] 01_triangulation_concept.png")
    make_quadrant_scatter(m)
    print("[ok] 02_quadrant_scatter.png")
    make_upside_top10(m)
    print("[ok] 03_upside_top10.png")
    make_downside_top10(m)
    print("[ok] 04_downside_top10.png")
    make_trading_companies(m)
    print("[ok] 05_trading_companies.png")
