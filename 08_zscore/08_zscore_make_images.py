"""
blog/09_進捗率Zscore.md 用の画像生成スクリプト。

生成画像:
  01_progress_distribution.png — Q1/Q2/Q3 進捗率の分布（売上 vs 営業利益）
  02_early_warning_top15.png   — 営業利益進捗率 Z-score 下位 15（早期警報）
  03_surprise_top15.png        — 営業利益進捗率 Z-score 上位 15（業績超過）
  04_sales_vs_op_scatter.png   — 売上 × 営業利益 進捗率 散布図（マージン分析）
  05_quarterly_pattern.png     — 四半期別 理論進捗率 vs 実測中央値

実行: python scripts/blog/08_progress_zscore_make_images.py
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

C_OP   = "#3498db"  # 営業利益
C_NS   = "#5a9a72"  # 売上
C_WARN = "#c87878"  # 警報
C_UP   = "#5a9a72"  # 業績超過
C_BG   = "#cccccc"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/08_progress_zscore")
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


# ── データ準備 ─────────────────────────────────────────────────────────────
def load_progress() -> pd.DataFrame:
    """決算短信 JSON から進捗率と Z-score を計算した DataFrame を返す。"""
    rows = []
    for f in STMTS.glob("*.json"):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {})
        perf = d.get("performance", {}).get("current") or {}
        rows.append({
            "code": meta.get("code"),
            "name": meta.get("company_name"),
            "fy_end": meta.get("fiscal_year_end"),
            "period_type": meta.get("period_type"),
            "kind": meta.get("kind"),
            "filing_date": meta.get("filing_date"),
            "net_sales": perf.get("net_sales"),
            "op_income": perf.get("operating_income"),
            "ord_income": perf.get("ordinary_income"),
            "net_income": perf.get("net_income"),
        })
    df = pd.DataFrame(rows)

    # 通期予想（最新提出）
    fc = df[(df["kind"] == "forecast") & (df["period_type"] == "FY")].copy()
    fc = fc.sort_values("filing_date").groupby(["code", "fy_end"]).tail(1)
    fc = fc[["code", "fy_end", "net_sales", "op_income", "ord_income", "net_income"]].rename(
        columns={"net_sales": "fc_net_sales", "op_income": "fc_op_income",
                 "ord_income": "fc_ord_income", "net_income": "fc_net_income"}
    )

    # 四半期累積実績（最新提出）
    qa = df[df["kind"].isin(["actual", "actual_secondary"]) &
            df["period_type"].isin(["Q1", "Q2", "Q3"])].copy()
    qa = qa.sort_values("filing_date").groupby(
        ["code", "fy_end", "period_type"]).tail(1)

    prog = qa.merge(fc, on=["code", "fy_end"])

    for m in ["net_sales", "op_income", "ord_income", "net_income"]:
        prog[f"prog_{m}"] = prog[m] / prog[f"fc_{m}"] * 100

    # Z-score（四半期別）
    for m in ["net_sales", "op_income", "ord_income", "net_income"]:
        col = f"prog_{m}"
        z_col = f"z_{col}"
        prog[z_col] = np.nan
        for q in ["Q1", "Q2", "Q3"]:
            mask = prog["period_type"] == q
            valid = prog.loc[mask, col].where(
                (prog.loc[mask, col] > 0) & (prog.loc[mask, col] < 300))
            mu, sd = valid.mean(), valid.std()
            if pd.notna(sd) and sd > 0:
                prog.loc[mask, z_col] = (prog.loc[mask, col] - mu) / sd

    prog["margin_gap"] = prog["prog_net_sales"] - prog["prog_op_income"]
    prog = apply_master_names(prog, code_col="code", name_col="name")
    return prog


# ── 1) 進捗率分布（Q1/Q2/Q3 × 売上 vs 営業利益） ───────────────────────────────
def make_progress_distribution(prog: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 7),
                             gridspec_kw=dict(hspace=0.45, wspace=0.25))

    expected = {"Q1": 25, "Q2": 50, "Q3": 75}

    for col_idx, q in enumerate(["Q1", "Q2", "Q3"]):
        sub = prog[prog["period_type"] == q]
        # 売上（上段）
        ax = axes[0, col_idx]
        s = sub["prog_net_sales"].dropna()
        s = s[(s > 0) & (s < 200)]
        if len(s) > 0:
            ax.hist(s, bins=20, color=C_NS, alpha=0.7,
                    edgecolor="white", linewidth=0.5)
            med = float(s.median())
            ax.axvline(expected[q], color="#999999", linestyle="--",
                       linewidth=1.0, alpha=0.7, label=f"理論 {expected[q]}%")
            ax.axvline(med, color="#202124", linestyle="-",
                       linewidth=1.2, alpha=0.9, label=f"中央 {med:.0f}%")
        ax.set_title(f"{q} 売上進捗率 (n={len(s)})",
                     fontsize=16, color=C_NS, fontweight="bold")
        ax.set_xlim(0, 150)
        ax.legend(loc="upper right", fontsize=16, frameon=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)

        # 営業利益（下段）
        ax = axes[1, col_idx]
        s = sub["prog_op_income"].dropna()
        s = s[(s > -50) & (s < 200)]
        if len(s) > 0:
            ax.hist(s, bins=25, color=C_OP, alpha=0.7,
                    edgecolor="white", linewidth=0.5)
            med = float(s.median())
            ax.axvline(expected[q], color="#999999", linestyle="--",
                       linewidth=1.0, alpha=0.7, label=f"理論 {expected[q]}%")
            ax.axvline(med, color="#202124", linestyle="-",
                       linewidth=1.2, alpha=0.9, label=f"中央 {med:.0f}%")
            ax.axvline(0, color=C_WARN, linewidth=0.8, alpha=0.6)
        ax.set_title(f"{q} 営業利益進捗率 (n={len(s)})",
                     fontsize=16, color=C_OP, fontweight="bold")
        ax.set_xlim(-30, 200)
        ax.legend(loc="upper right", fontsize=16, frameon=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)

    fig.suptitle("四半期別 進捗率の分布  ―  売上は理論線付近、営業利益は左右に分散",
                 fontsize=20, fontweight="bold", color=C_TEXT, y=1.00)
    _savefig_vpad(fig, OUT_DIR / "01_progress_distribution.png")
    plt.close(fig)


# ── 2) 早期警報 Top15 ─────────────────────────────────────────────────────
def make_early_warning(prog: pd.DataFrame) -> None:
    ew = prog.dropna(subset=["z_prog_op_income", "prog_op_income", "prog_net_sales"])
    ew = ew[ew["prog_op_income"].between(-50, 200) &
            ew["prog_net_sales"].between(0, 200)]
    top = ew.nsmallest(15, "z_prog_op_income").iloc[::-1]

    fig, ax = plt.subplots(figsize=(14, 7.5))
    y = np.arange(len(top))

    # 警報レベルで色分け
    colors = [C_WARN if z <= -2.5 else "#aaaaaa" if z <= -1.5 else "#f1c40f"
              for z in top["z_prog_op_income"]]
    ax.barh(y, top["z_prog_op_income"], color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    for i, (_, r) in enumerate(top.iterrows()):
        label = f"{r['z_prog_op_income']:.2f}  |  営利進捗 {r['prog_op_income']:.1f}%  /  売上進捗 {r['prog_net_sales']:.1f}%"
        ax.text(r["z_prog_op_income"] - 0.1, i, label,
                va="center", ha="right",
                fontsize=16, color=C_TEXT, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name'][:14]} ({r['period_type']})"
                        for _, r in top.iterrows()], fontsize=16)
    ax.axvline(-2.5, color=C_WARN, linestyle=":", linewidth=0.8,
               label="重大警報 (Z ≤ -2.5)")
    ax.axvline(-1.5, color="#aaaaaa", linestyle=":", linewidth=0.8,
               label="明確警報 (Z ≤ -1.5)")
    ax.axvline(0, color="#999999", linewidth=0.7)
    ax.set_xlim(top["z_prog_op_income"].min() * 1.05, 0.5)
    ax.set_xlabel("営業利益進捗率 Z-score", fontsize=16, color=C_TEXT)
    ax.legend(loc="lower left", fontsize=16, frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    ax.set_title("🚨 早期警報 Top 15  ―  営業利益進捗率 Z-score 下位（下方修正リスク）",
                 fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    _savefig_vpad(fig, OUT_DIR / "02_early_warning_top15.png")
    plt.close(fig)


# ── 3) 業績超過 Top15 ─────────────────────────────────────────────────────
def make_surprise(prog: pd.DataFrame) -> None:
    ew = prog.dropna(subset=["z_prog_op_income", "prog_op_income", "prog_net_sales"])
    ew = ew[ew["prog_op_income"].between(-50, 200) &
            ew["prog_net_sales"].between(0, 200)]
    top = ew.nlargest(15, "z_prog_op_income").iloc[::-1]

    fig, ax = plt.subplots(figsize=(14, 7.5))
    y = np.arange(len(top))

    colors = [C_UP if z >= 2.5 else "#3498db" if z >= 1.5 else "#85c1e9"
              for z in top["z_prog_op_income"]]
    ax.barh(y, top["z_prog_op_income"], color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    for i, (_, r) in enumerate(top.iterrows()):
        label = f"{r['z_prog_op_income']:.2f}  |  営利進捗 {r['prog_op_income']:.1f}%  /  売上進捗 {r['prog_net_sales']:.1f}%"
        ax.text(r["z_prog_op_income"] + 0.1, i, label,
                va="center", ha="left",
                fontsize=16, color=C_TEXT, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name'][:14]} ({r['period_type']})"
                        for _, r in top.iterrows()], fontsize=16)
    ax.axvline(2.5, color=C_UP, linestyle=":", linewidth=0.8,
               label="重大上振れ (Z ≥ +2.5)")
    ax.axvline(1.5, color="#3498db", linestyle=":", linewidth=0.8,
               label="明確上振れ (Z ≥ +1.5)")
    ax.axvline(0, color="#999999", linewidth=0.7)
    ax.set_xlim(-0.5, top["z_prog_op_income"].max() * 1.45)
    ax.set_xlabel("営業利益進捗率 Z-score", fontsize=16, color=C_TEXT)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    ax.set_title("🚀 業績超過 Top 15  ―  営業利益進捗率 Z-score 上位（上方修正期待）",
                 fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    _savefig_vpad(fig, OUT_DIR / "03_surprise_top15.png")
    plt.close(fig)


# ── 4) 売上 × 営業利益 進捗率 散布図（マージン分析） ──────────────────────────
def make_sales_vs_op_scatter(prog: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5),
                             gridspec_kw=dict(wspace=0.25))
    fig.subplots_adjust(top=0.78)

    expected = {"Q1": 25, "Q2": 50, "Q3": 75}

    for ax, q in zip(axes, ["Q1", "Q2", "Q3"]):
        sub = prog[prog["period_type"] == q].copy()
        sub = sub.dropna(subset=["prog_net_sales", "prog_op_income"])
        sub = sub[sub["prog_net_sales"].between(0, 200) &
                  sub["prog_op_income"].between(-50, 200)]

        e = expected[q]

        # ゾーン背景
        ax.axhspan(-50, e, xmin=(e - 0) / 200, xmax=1.0,
                   facecolor=C_WARN, alpha=0.04)  # 右下 = 売上順調 × 利益遅れ

        # 全銘柄
        ax.scatter(sub["prog_net_sales"], sub["prog_op_income"],
                   s=22, color=C_BG, alpha=0.5, edgecolors="none")

        # マージン悪化（売上 ≥ 想定 × 営利 < 想定）
        warn = sub[(sub["prog_net_sales"] >= e) & (sub["prog_op_income"] < e)]
        ax.scatter(warn["prog_net_sales"], warn["prog_op_income"],
                   s=50, color=C_WARN, alpha=0.85, edgecolors="white",
                   linewidth=0.5, label=f"マージン悪化 ({len(warn)})")

        # 45 度ライン
        ax.plot([0, 200], [0, 200], color="#777777", linestyle="--",
                linewidth=0.7, alpha=0.5, label="45° (売上=利益)")

        # 想定進捗率
        ax.axvline(e, color="#999999", linestyle=":", linewidth=0.7)
        ax.axhline(e, color="#999999", linestyle=":", linewidth=0.7)

        ax.set_xlim(0, max(sub["prog_net_sales"].max() * 1.05, 100))
        ax.set_ylim(-30, max(sub["prog_op_income"].max() * 1.05, 100))
        ax.set_xlabel("売上進捗率（%）", fontsize=16, color=C_TEXT)
        if ax is axes[0]:
            ax.set_ylabel("営業利益進捗率（%）", fontsize=16, color=C_TEXT)
        ax.set_title(f"{q}（想定 {e}%、n={len(sub)}）",
                     fontsize=16, fontweight="bold", color=C_TEXT, pad=24)
        ax.grid(color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(loc="lower right", fontsize=16, frameon=False)

    fig.suptitle("売上 × 営業利益 進捗率の散布図  ―  45° 線下が「売上順調なのに利益遅れ＝マージン悪化」ゾーン",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=0.97)
    _savefig_vpad(fig, OUT_DIR / "04_sales_vs_op_scatter.png")
    plt.close(fig)


# ── 5) 四半期別 理論進捗率 vs 実測中央値 ─────────────────────────────────────
def make_quarterly_pattern(prog: pd.DataFrame) -> None:
    rows = []
    for q in ["Q1", "Q2", "Q3"]:
        sub = prog[prog["period_type"] == q]
        for m, label in [("prog_net_sales", "売上"),
                         ("prog_op_income", "営業利益"),
                         ("prog_ord_income", "経常利益"),
                         ("prog_net_income", "純利益")]:
            v = sub[m].dropna()
            v = v[(v > 0) & (v < 300)]
            if len(v) < 5:
                continue
            rows.append({"q": q, "metric": label,
                         "median": v.median(), "n": len(v)})
    df = pd.DataFrame(rows)

    expected = {"Q1": 25, "Q2": 50, "Q3": 75}

    fig, ax = plt.subplots(figsize=(13, 6))

    metrics = ["売上", "営業利益", "経常利益", "純利益"]
    colors = {"売上": C_NS, "営業利益": C_OP,
              "経常利益": "#888888", "純利益": "#aaaaaa"}
    quarters = ["Q1", "Q2", "Q3"]
    x = np.arange(len(quarters))
    bw = 0.18

    for i, metric in enumerate(metrics):
        sub = df[df["metric"] == metric].set_index("q").reindex(quarters)
        ax.bar(x + (i - 1.5) * bw, sub["median"], width=bw,
               color=colors[metric], alpha=0.85,
               edgecolor="white", linewidth=0.8, label=metric)
        for xi, v in zip(x + (i - 1.5) * bw, sub["median"]):
            ax.text(xi, v + 1.5, f"{v:.0f}",
                    ha="center", va="bottom", fontsize=16,
                    fontweight="bold", color=colors[metric])

    # 理論進捗率ライン
    for q, e in expected.items():
        xi = quarters.index(q)
        ax.hlines(e, xi - 0.5, xi + 0.5, color="#444444",
                  linestyle="--", linewidth=1.4)
        ax.text(xi + 0.45, e + 1.5, f"理論 {e}%",
                fontsize=16, color="#444444", ha="right", va="bottom",
                style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(quarters, fontsize=16, fontweight="bold")
    ax.set_ylabel("進捗率の中央値（%）", fontsize=16, color=C_TEXT)
    ax.legend(loc="upper left", fontsize=16, frameon=False)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "四半期別の進捗率パターン  ―  営業利益が売上より進捗率高い（上期偏重の利益構造）",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "05_quarterly_pattern.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    prog = load_progress()
    print(f"[load] {len(prog)} 行（Q1-Q3 累積実績と通期予想のマッチ）")
    print(prog["period_type"].value_counts())

    make_progress_distribution(prog)
    print("[ok] 01_progress_distribution.png")
    make_early_warning(prog)
    print("[ok] 02_early_warning_top15.png")
    make_surprise(prog)
    print("[ok] 03_surprise_top15.png")
    make_sales_vs_op_scatter(prog)
    print("[ok] 04_sales_vs_op_scatter.png")
    make_quarterly_pattern(prog)
    print("[ok] 05_quarterly_pattern.png")
