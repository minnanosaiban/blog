"""
blog/11_三角検証.md 用の画像生成スクリプト。

生成画像:
  01_triangulation_concept.png — 3 ソース×3 ペア比較の概念図
  02_quadrant_scatter.png      — ガイダンスvs実績 × コンセンサスvsガイダンス 4 象限散布図
  03_upside_top10.png          — 上方修正期待 Top10（保守ガイダンス×アナリスト強気）
  04_downside_top10.png        — 達成困難 Top10（強気ガイダンス×アナリスト懐疑）
  05_trading_companies.png     — 総合商社 8 社の三角検証 × アクルーアル接続

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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── デザイン設定 ────────────────────────────────────────────────────────────
mpl.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP"]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["figure.facecolor"] = "white"
mpl.rcParams["axes.facecolor"] = "white"
mpl.rcParams["savefig.facecolor"] = "white"
mpl.rcParams["savefig.bbox"] = "tight"
mpl.rcParams["savefig.dpi"] = 144
mpl.rcParams["savefig.pad_inches"] = 0        # left/right/top: no padding
mpl.rcParams["axes.titlepad"] = 30
mpl.rcParams["font.size"] = 16
mpl.rcParams["axes.titlesize"] = 20
mpl.rcParams["axes.labelsize"] = 16
mpl.rcParams["xtick.labelsize"] = 16
mpl.rcParams["ytick.labelsize"] = 16
mpl.rcParams["legend.fontsize"] = 16

C_ACT  = "#444444"  # 実績
C_GUI  = "#777777"  # ガイダンス
C_CONS = "#aaaaaa"  # コンセンサス
C_UP   = "#5a9a72"  # 上方修正期待
C_WARN = "#c87878"  # 達成困難
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/10_triangulation")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _savefig_vpad(fig: plt.Figure, path: Path, bpad: float = 0.5) -> None:
    """下のみ bpad インチの余白を追加して保存する（上・左右は余白なし）。"""
    import io
    import numpy as np
    buf = io.BytesIO()
    fig.savefig(buf, bbox_inches="tight", pad_inches=0, format="png")
    buf.seek(0)
    img = plt.imread(buf)                            # RGBA float32 (H, W, 4)
    pad_rows = max(1, round(bpad * fig.dpi))
    white = np.ones((pad_rows, img.shape[1], img.shape[2]), dtype=img.dtype)
    plt.imsave(str(path), np.vstack([img, white]), dpi=fig.dpi)


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


# ── 1) 三角検証の概念図 ────────────────────────────────────────────────────
def make_concept() -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # 3 頂点
    nodes = {
        "actual":   (2.0, 5.8, C_ACT,  "実績\n（決算短信 actual FY）", "data/statements/{code}_*_FY.json"),
        "guidance": (9.0, 5.8, C_GUI,  "ガイダンス\n（決算短信 forecast FY）", "data/statements/{code}_*_forecast_FY.json"),
        "consensus": (5.5, 1.2, C_CONS, "アナリスト\nコンセンサス\n（rakunav 213 EPS予）", "data/rakunav/213_EPS.csv"),
    }
    for key, (x, y, color, label, src) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - 1.5, y - 0.7), 3.0, 1.4,
                                    boxstyle="round,pad=0.08",
                                    linewidth=2.2, edgecolor=color,
                                    facecolor="white"))
        ax.text(x, y + 0.15, label, ha="center", va="center",
                fontsize=16, fontweight="bold", color=color)
        ax.text(x, y - 0.45, src, ha="center", va="center",
                fontsize=16, color=C_TEXT_SUB, style="italic")

    # 3 ペア
    pairs = [
        # 上辺: ガイダンス vs 実績
        ((nodes["actual"][0]+1.5, nodes["actual"][1]),
         (nodes["guidance"][0]-1.5, nodes["guidance"][1]),
         "ガイダンス − 実績\nプラス = 強気 / マイナス = 保守"),
        # 右辺: コンセンサス vs ガイダンス
        ((nodes["guidance"][0]-0.3, nodes["guidance"][1]-0.7),
         (nodes["consensus"][0]+1.2, nodes["consensus"][1]+0.3),
         "コンセンサス − ガイダンス\nプラス = アナリスト強気"),
        # 左辺: コンセンサス vs 実績
        ((nodes["actual"][0]+0.3, nodes["actual"][1]-0.7),
         (nodes["consensus"][0]-1.2, nodes["consensus"][1]+0.3),
         "コンセンサス − 実績\nアナリストの来期成長期待"),
    ]
    for (x1, y1), (x2, y2), label in pairs:
        a = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle="<->", mutation_scale=22,
                            color="#888888", linewidth=1.5)
        ax.add_patch(a)
        # ラベル
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=16, ha="center", va="center",
                color="#444444", fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="#cccccc",
                          boxstyle="round,pad=0.25"))

    ax.text(5.5, 6.7, "三角検証  ―  3 ソース × 3 ペア比較",
            fontsize=20, fontweight="bold", color=C_TEXT,
            ha="center", va="center")
    ax.text(5.5, 0.2,
            "保守ガイダンス × アナリスト強気 = 上方修正期待大\n"
            "強気ガイダンス × アナリスト懐疑 = 達成困難",
            fontsize=16, ha="center", va="center",
            color=C_TEXT_SUB, style="italic")

    _savefig_vpad(fig, OUT_DIR / "01_triangulation_concept.png")
    plt.close(fig)


# ── 2) 4 象限散布図 ────────────────────────────────────────────────────────
def make_quadrant_scatter(m: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 8))

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
    ax.set_xlabel("ガイダンス − 実績（%）  ← 保守     強気 →",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("コンセンサス − ガイダンス（%）  ← 懐疑    強気 →",
                  fontsize=16, color=C_TEXT)
    ax.set_title(f"三角検証 4 象限マップ  ―  決算短信 211 銘柄",
                 fontsize=20, fontweight="bold", color=C_TEXT,
                 pad=14, loc="left")
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

    fig, ax = plt.subplots(figsize=(13.5, 7))
    y = np.arange(len(top))
    bw = 0.35

    ax.barh(y - bw / 2, top["guide_vs_actual_pct"], height=bw,
            color="#85c1e9", alpha=0.85, edgecolor="white", linewidth=0.8,
            label="ガイダンス − 実績（左軸）")
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
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "03_upside_top10.png")
    plt.close(fig)


# ── 4) 達成困難 Top10 ────────────────────────────────────────────────
def make_downside_top10(m: pd.DataFrame) -> None:
    sub = m[(m["guide_vs_actual_pct"] > 10) & (m["consensus_vs_guide_pct"] < -5)]
    sub = sub[sub["guide_vs_actual_pct"] < 500]  # 極端値除外
    top = sub.nsmallest(10, "consensus_vs_guide_pct").iloc[::-1]

    fig, ax = plt.subplots(figsize=(13.5, 7))
    y = np.arange(len(top))
    bw = 0.35

    ax.barh(y - bw / 2, top["guide_vs_actual_pct"], height=bw,
            color="#f1c40f", alpha=0.85, edgecolor="white", linewidth=0.8,
            label="ガイダンス − 実績（強気プラス）")
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
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "04_downside_top10.png")
    plt.close(fig)


# ── 5) 総合商社 8 社の三角検証 × 連載10 アクルーアル接続 ──────────────────
def make_trading_companies(m: pd.DataFrame) -> None:
    """総合商社 8 社の三角検証 + 連載10 で算出した平均アクルーアル比率を並べる。"""
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

    fig, axes = plt.subplots(1, 2, figsize=(14, 6),
                             gridspec_kw=dict(width_ratios=[1.3, 1], wspace=0.35))

    # 左: 三角検証バー（ガイダンス vs 実績、コンセンサス vs ガイダンス）
    ax_l = axes[0]
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

    y = np.arange(len(rdf))
    bw = 0.35
    ax_l.barh(y - bw / 2, rdf["ga"], height=bw,
              color="#85c1e9", alpha=0.85, edgecolor="white", linewidth=0.8,
              label="ガイダンス − 実績")
    ax_l.barh(y + bw / 2, rdf["cg"], height=bw,
              color=C_CONS, alpha=0.85, edgecolor="white", linewidth=0.8,
              label="コンセンサス − ガイダンス")

    for i, r in rdf.iterrows():
        ax_l.text(r["ga"] + (1 if r["ga"] >= 0 else -1), i - bw / 2,
                  f"{r['ga']:+.1f}%", va="center",
                  ha="left" if r["ga"] >= 0 else "right",
                  fontsize=16, color="#3498db", fontweight="bold")
        ax_l.text(r["cg"] + (1 if r["cg"] >= 0 else -1), i + bw / 2,
                  f"{r['cg']:+.1f}%", va="center",
                  ha="left" if r["cg"] >= 0 else "right",
                  fontsize=16, color=C_CONS, fontweight="bold")

    ax_l.axvline(0, color="#444444", linewidth=0.8)
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([f"{r['code']} {r['label']}" for _, r in rdf.iterrows()],
                         fontsize=16)
    ax_l.set_xlabel("乖離率（%）", fontsize=16, color=C_TEXT_SUB)
    ax_l.legend(loc="lower right", fontsize=16, frameon=False)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("三角検証（連載11）",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 右: 連載10 のアクルーアル比率
    ax_r = axes[1]
    colors = ["#5a9a72" if a < -0.01 else "#85c1e9" if a < 0 else "#F39C12"
              for a in rdf["accrual"]]
    ax_r.barh(y, rdf["accrual"], color=colors, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, r in rdf.iterrows():
        ax_r.text(r["accrual"] - 0.001, i, f"{r['accrual']:+.4f}",
                  va="center", ha="right",
                  fontsize=16, color=C_TEXT, fontweight="bold")
    ax_r.axvline(-0.05, color="#5a9a72", linestyle="--", linewidth=0.7, alpha=0.6)
    ax_r.axvline(0, color="#999999", linewidth=0.7)
    ax_r.set_yticks(y)
    ax_r.set_yticklabels([""] * len(rdf))
    ax_r.set_xlabel("7 年平均アクルーアル比率", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_xlim(-0.05, 0.01)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("アクルーアル（連載10）",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle(
        "総合商社 8 社  ―  三角検証 × アクルーアル の合流  ―  健全な利益の質 × 保守ガイダンス × アナリスト強気",
        fontsize=20, fontweight="bold", color=C_TEXT, y=1.02,
    )
    _savefig_vpad(fig, OUT_DIR / "05_trading_companies.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    m = load_triangulation()
    print(f"[load] {len(m)} 銘柄で三角検証可能")

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
