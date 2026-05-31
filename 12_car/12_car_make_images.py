"""
blog/13_CARイベントスタディ.md 用の画像生成スクリプト。

生成画像:
  01_car_concept.png         — CAR イベントスタディの概念図
  02_category_car.png        — カテゴリ別 CAR の分布（ボックス + 平均）
  03_surprise_scatter.png    — 純利益変化率 × 20 営業日 CAR 散布図
  04_periods_comparison.png  — 集計期間別（5/10/20/30 日）CAR 比較
  05_top_bottom_cases.png    — CAR Top5 / Bottom5 のケーススタディ

実行: python scripts/blog/12_car_event_study_make_images.py
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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from utils.master_names import load_price_targets_names


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

C_GOOD = "#5a9a72"
C_BAD  = "#c87878"
C_NEU  = "#7f8c8d"
C_STOCK = "#3498db"
C_BENCH = "#888888"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/12_car_event_study")
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


STMTS  = Path(r"C:/stock_analysis/data/statements")
PRICES = Path(r"C:/stock_analysis/data/prices/stocks/daily")
MACRO  = Path(r"C:/stock_analysis/data/prices/macro/daily")


def load_car_dataset() -> pd.DataFrame:
    """決算 actual FY × actual_secondary 前期 × yfinance × N225 で CAR を計算。"""
    n225 = pd.read_parquet(MACRO / "N225.parquet", columns=["Close"]).reset_index()
    n225.columns = ["date", "n225_close"]
    n225["date"] = pd.to_datetime(n225["date"])

    rows = []
    for f in STMTS.glob("*_FY.json"):
        if "forecast" in f.name:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {})
        if meta.get("kind") != "actual":
            continue
        perf = d.get("performance", {}).get("current") or {}
        rows.append({
            "code": meta.get("code"),
            "fy_end": meta.get("fiscal_year_end"),
            "filing_date": meta.get("filing_date"),
            "net_income": perf.get("net_income"),
        })
    df = pd.DataFrame(rows).dropna(subset=["code", "filing_date", "net_income"])
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df = df.dropna(subset=["filing_date"])

    rows2 = []
    for f in STMTS.glob("*_FY.json"):
        if "forecast" in f.name:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {})
        if meta.get("kind") != "actual_secondary":
            continue
        perf = d.get("performance", {}).get("current") or {}
        rows2.append({
            "code": meta.get("code"),
            "fy_end": meta.get("fiscal_year_end"),
            "prv_net_income": perf.get("net_income"),
        })
    df_prv = pd.DataFrame(rows2).dropna(subset=["code", "fy_end", "prv_net_income"])

    df["prev_fy_year"] = df["fy_end"].astype(str).str[:4].astype(int) - 1
    df_prv["fy_year"] = df_prv["fy_end"].astype(str).str[:4].astype(int)
    m = df.merge(df_prv[["code", "fy_year", "prv_net_income"]],
                 left_on=["code", "prev_fy_year"],
                 right_on=["code", "fy_year"], how="inner")
    m["ni_change_pct"] = (m["net_income"] - m["prv_net_income"]) / m["prv_net_income"].abs() * 100

    # 各銘柄について N=5/10/20/30 営業日の CAR を計算
    results = []
    for _, r in m.iterrows():
        pq = PRICES / f"{r['code']}.parquet"
        if not pq.exists():
            continue
        try:
            sp = pd.read_parquet(pq, columns=["Close"]).reset_index()
        except Exception:
            continue
        sp.columns = ["date", "close"]
        sp["date"] = pd.to_datetime(sp["date"])
        after = sp[sp["date"] > r["filing_date"]].head(32)
        if len(after) < 6:
            continue
        after = after.merge(n225[["date", "n225_close"]], on="date", how="left").dropna()
        if len(after) < 6:
            continue
        p0 = after["close"].iloc[0]
        b0 = after["n225_close"].iloc[0]
        row = {
            "code": r["code"],
            "filing_date": r["filing_date"],
            "ni_change_pct": r["ni_change_pct"],
        }
        for n in [5, 10, 20, 30]:
            if len(after) > n:
                stock_ret = (after["close"].iloc[n] / p0 - 1) * 100
                bench_ret = (after["n225_close"].iloc[n] / b0 - 1) * 100
                row[f"car_{n}"] = stock_ret - bench_ret
                row[f"stock_ret_{n}"] = stock_ret
                row[f"bench_ret_{n}"] = bench_ret
        results.append(row)
    return pd.DataFrame(results)


def categorize(ni: float) -> str:
    if pd.isna(ni):
        return "unknown"
    if ni >= 20:
        return "良決算 (純利益 +20% 以上)"
    if ni <= -20:
        return "悪決算 (純利益 -20% 以下)"
    return "中立 (±20% 以内)"


# ── 1) コンセプト図 ────────────────────────────────────────────────────────
def make_concept(rdf: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # タイムライン
    ax.plot([1, 11], [4, 4], color="#666666", linewidth=2, zorder=1)
    # 決算発表日
    ax.scatter([4], [4], s=300, color="#aaaaaa", edgecolor="white",
               linewidth=2, zorder=5)
    ax.text(4, 5.0, "決算発表日\n(filing_date)", ha="center", va="center",
            fontsize=16, fontweight="bold", color="#aaaaaa")

    # 観測期間
    for x, label, color in [(5.5, "5 営業日", "#3498db"),
                             (7.0, "10 営業日", "#3498db"),
                             (8.5, "20 営業日", "#3498db"),
                             (10.0, "30 営業日", "#888888")]:
        ax.axvline(x, color=color, linestyle=":", linewidth=1.2, alpha=0.6,
                   ymin=0.42, ymax=0.65)
        ax.text(x, 4.35, label, fontsize=16, ha="center", color=color,
                fontweight="bold")
    # 矢印
    a = FancyArrowPatch((4, 3.5), (10.5, 3.5), arrowstyle="->",
                        mutation_scale=18, color="#666666", linewidth=1.5)
    ax.add_patch(a)
    ax.text(7.5, 3.15, "決算後の株価リターンを観測",
            fontsize=16, ha="center", color="#666666", style="italic")

    # CAR 計算式
    ax.add_patch(FancyBboxPatch((0.5, 1.0), 11, 1.5,
                                 boxstyle="round,pad=0.08",
                                 linewidth=1.5, edgecolor="#aaaaaa",
                                 facecolor="#f8fafd"))
    ax.text(6, 2.1, "CAR (Cumulative Abnormal Return)",
            fontsize=16, fontweight="bold", color=C_TEXT,
            ha="center", va="center")
    ax.text(6, 1.5, "= 銘柄リターン − ベンチマーク(N225)リターン",
            fontsize=16, color=C_TEXT, ha="center", va="center")

    # サンプル
    n = len(rdf)
    n_good = (rdf["ni_change_pct"] >= 20).sum()
    n_bad = (rdf["ni_change_pct"] <= -20).sum()
    n_neu = ((rdf["ni_change_pct"] > -20) & (rdf["ni_change_pct"] < 20)).sum()
    ax.text(6, 6.3, "CAR イベントスタディの設計",
            fontsize=20, fontweight="bold", color=C_TEXT,
            ha="center", va="center")
    ax.text(6, 0.4,
            f"本記事のサンプル: 良決算 {n_good} 件 / 中立 {n_neu} 件 / 悪決算 {n_bad} 件  (合計 {n} 件)",
            fontsize=16, ha="center", color=C_TEXT_SUB, style="italic")

    _savefig_vpad(fig, OUT_DIR / "01_car_concept.png")
    plt.close(fig)


# ── 2) カテゴリ別 CAR ────────────────────────────────────────────────────
def make_category_car(rdf: pd.DataFrame) -> None:
    rdf = rdf.copy()
    rdf["category"] = rdf["ni_change_pct"].apply(categorize)
    rdf = rdf[rdf["car_20"].between(-50, 50)]

    cats = ["良決算 (純利益 +20% 以上)",
            "中立 (±20% 以内)",
            "悪決算 (純利益 -20% 以下)"]
    colors = [C_GOOD, C_NEU, C_BAD]

    fig, ax = plt.subplots(figsize=(13, 6.5))

    data = [rdf[rdf["category"] == c]["car_20"].dropna() for c in cats]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                    medianprops=dict(color="white", linewidth=2),
                    flierprops=dict(marker="o", markersize=3, alpha=0.4))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)
        patch.set_edgecolor(color)
        patch.set_linewidth(1.2)

    # 平均と n を表示
    for i, (c, color) in enumerate(zip(cats, colors)):
        sub = rdf[rdf["category"] == c]["car_20"].dropna()
        if sub.empty:
            continue
        ax.scatter([i + 1], [sub.mean()], s=180, color=color,
                   edgecolor="white", linewidth=2, zorder=5, marker="D")
        ax.text(i + 1, sub.mean() + 1.5,
                f"平均 {sub.mean():+.2f}%",
                ha="center", va="bottom", fontsize=16, fontweight="bold",
                color=color)
        win = (sub > 0).mean() * 100
        ax.text(i + 1, -42, f"n={len(sub)}\n勝率 {win:.1f}%",
                ha="center", va="bottom", fontsize=16, color=C_TEXT_SUB)

    ax.axhline(0, color="#444444", linewidth=0.8)
    ax.set_xticks(range(1, len(cats) + 1))
    ax.set_xticklabels(cats, fontsize=16)
    ax.set_ylabel("20 営業日 CAR（%、N225 比）",
                  fontsize=16, color=C_TEXT)
    ax.set_ylim(-45, 45)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "決算カテゴリ別 CAR の分布  ―  ◆ が平均値",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )

    fig.text(0.5, -0.02,
             "本データセットでは「良決算カテゴリも平均 CAR がマイナス」 ＝ 日本市場の事前織り込みの強さを示唆",
             fontsize=16, color=C_TEXT_SUB, ha="center", style="italic")

    _savefig_vpad(fig, OUT_DIR / "02_category_car.png")
    plt.close(fig)


# ── 3) 散布図 ──────────────────────────────────────────────────────────────
def make_scatter(rdf: pd.DataFrame) -> None:
    sub = rdf[rdf["ni_change_pct"].between(-150, 300) &
              rdf["car_20"].between(-40, 40)].copy()
    corr = sub["ni_change_pct"].corr(sub["car_20"])

    fig, ax = plt.subplots(figsize=(13, 7))

    # ゾーン背景
    ax.axhspan(0, 40, xmin=(20 - (-150)) / 450, xmax=1.0,
               facecolor=C_GOOD, alpha=0.03)
    ax.axhspan(-40, 0, xmin=0, xmax=(-20 - (-150)) / 450,
               facecolor=C_BAD, alpha=0.03)

    # 各点をカテゴリで色分け
    for _, r in sub.iterrows():
        cat = categorize(r["ni_change_pct"])
        color = C_GOOD if "良" in cat else C_BAD if "悪" in cat else C_NEU
        ax.scatter(r["ni_change_pct"], r["car_20"],
                   s=30, color=color, alpha=0.55,
                   edgecolors="white", linewidth=0.3)

    # 回帰直線
    valid = sub.dropna(subset=["ni_change_pct", "car_20"])
    if len(valid) > 10:
        z = np.polyfit(valid["ni_change_pct"], valid["car_20"], 1)
        xx = np.linspace(valid["ni_change_pct"].min(),
                         valid["ni_change_pct"].max(), 100)
        ax.plot(xx, np.polyval(z, xx), color=C_TEXT,
                linewidth=2.0, linestyle="--",
                label=f"回帰直線 (傾き {z[0]:.3f})")

    ax.axhline(0, color="#777777", linewidth=0.7)
    ax.axvline(0, color="#777777", linewidth=0.7)
    ax.axvline(20, color=C_GOOD, linestyle=":", linewidth=0.6, alpha=0.5)
    ax.axvline(-20, color=C_BAD, linestyle=":", linewidth=0.6, alpha=0.5)

    ax.set_xlabel("純利益前期比変化率（%）", fontsize=16, color=C_TEXT)
    ax.set_ylabel("20 営業日 CAR（%）", fontsize=16, color=C_TEXT)
    ax.set_xlim(-150, 300)
    ax.set_ylim(-40, 40)
    ax.set_title(
        f"純利益変化率 × CAR 散布図  ―  相関 {corr:+.3f}（n={len(sub)}）",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    ax.legend(loc="upper right", fontsize=16, frameon=False)
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    _savefig_vpad(fig, OUT_DIR / "03_surprise_scatter.png")
    plt.close(fig)


# ── 4) 期間別 CAR 比較 ───────────────────────────────────────────────────
def make_periods(rdf: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 6))

    periods = [5, 10, 20, 30]
    x = np.arange(len(periods))
    bw = 0.27

    good_means, bad_means, neu_means = [], [], []
    good_ns, bad_ns, neu_ns = [], [], []
    for n in periods:
        col = f"car_{n}"
        good = rdf[(rdf["ni_change_pct"] >= 20) & rdf[col].between(-50, 50)][col]
        bad = rdf[(rdf["ni_change_pct"] <= -20) & rdf[col].between(-50, 50)][col]
        neu = rdf[(rdf["ni_change_pct"] > -20) & (rdf["ni_change_pct"] < 20)
                  & rdf[col].between(-50, 50)][col]
        good_means.append(good.mean())
        bad_means.append(bad.mean())
        neu_means.append(neu.mean())
        good_ns.append(len(good))
        bad_ns.append(len(bad))
        neu_ns.append(len(neu))

    ax.bar(x - bw, good_means, width=bw, color=C_GOOD, alpha=0.85,
           edgecolor="white", linewidth=0.8, label="良決算 (+20%以上)")
    ax.bar(x, neu_means, width=bw, color=C_NEU, alpha=0.85,
           edgecolor="white", linewidth=0.8, label="中立")
    ax.bar(x + bw, bad_means, width=bw, color=C_BAD, alpha=0.85,
           edgecolor="white", linewidth=0.8, label="悪決算 (-20%以下)")

    for xi, v in zip(x - bw, good_means):
        ax.text(xi, v + (0.1 if v >= 0 else -0.15), f"{v:+.2f}%",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=16, fontweight="bold", color=C_GOOD)
    for xi, v in zip(x, neu_means):
        ax.text(xi, v + (0.1 if v >= 0 else -0.15), f"{v:+.2f}%",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=16, fontweight="bold", color=C_NEU)
    for xi, v in zip(x + bw, bad_means):
        ax.text(xi, v + (0.1 if v >= 0 else -0.15), f"{v:+.2f}%",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=16, fontweight="bold", color=C_BAD)

    ax.axhline(0, color="#444444", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p} 営業日\n(n良={g}/中={ne}/悪={b})"
                        for p, g, ne, b in zip(periods, good_ns, neu_ns, bad_ns)],
                       fontsize=16)
    ax.set_ylabel("平均 CAR（%、N225 比）", fontsize=16, color=C_TEXT)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "集計期間別 平均 CAR  ―  全カテゴリで平均マイナス（PEAD 弱、事前織り込みの強さ）",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "04_periods_comparison.png")
    plt.close(fig)


# ── 5) Top / Bottom ケーススタディ ─────────────────────────────────────────
def make_top_bottom(rdf: pd.DataFrame, names: dict[str, str]) -> None:
    sub = rdf[rdf["car_20"].between(-60, 60)].copy()
    top = sub.nlargest(5, "car_20")
    bot = sub.nsmallest(5, "car_20")

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 6),
                                     gridspec_kw=dict(wspace=0.5))

    # Top
    y = np.arange(len(top))[::-1]
    ax_l.barh(y, top["car_20"], color=C_GOOD, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, (yi, (_, r)) in enumerate(zip(y, top.iterrows())):
        label = f"+{r['car_20']:.1f}%  (NI {r['ni_change_pct']:+.0f}% / 株価 {r['stock_ret_20']:+.1f}%)"
        ax_l.text(r["car_20"] + 0.5, yi, label,
                  va="center", fontsize=16, fontweight="bold", color=C_GOOD)
    ax_l.set_yticks(y)
    ax_l.set_yticklabels(
        [f"{r['code']} {names.get(r['code'], '')[:10]}\n  {r['filing_date'].strftime('%Y-%m-%d')}"
         for _, r in top.iterrows()], fontsize=16)
    ax_l.set_xlabel("20 営業日 CAR（%）", fontsize=16, color=C_TEXT_SUB)
    ax_l.set_xlim(0, top["car_20"].max() * 1.3)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("★ CAR Top5  ―  N225 を大きくアウトパフォーム",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # Bottom
    y = np.arange(len(bot))[::-1]
    ax_r.barh(y, bot["car_20"], color=C_BAD, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, (yi, (_, r)) in enumerate(zip(y, bot.iterrows())):
        label = f"{r['car_20']:.1f}%  (NI {r['ni_change_pct']:+.0f}% / 株価 {r['stock_ret_20']:+.1f}%)"
        ax_r.text(r["car_20"] - 0.5, yi, label,
                  va="center", ha="right",
                  fontsize=16, fontweight="bold", color=C_BAD)
    ax_r.set_yticks(y)
    ax_r.set_yticklabels(
        [f"{r['code']} {names.get(r['code'], '')[:10]}\n  {r['filing_date'].strftime('%Y-%m-%d')}"
         for _, r in bot.iterrows()], fontsize=16)
    ax_r.set_xlabel("20 営業日 CAR（%）", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_xlim(bot["car_20"].min() * 1.3, 0)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("⚠ CAR Bottom5  ―  N225 を大きくアンダーパフォーム",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle("極端事例のケーススタディ  ―  CAR の振れ幅は大きい",
                 fontsize=20, fontweight="bold", color=C_TEXT, y=1.02)
    _savefig_vpad(fig, OUT_DIR / "05_top_bottom_cases.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rdf = load_car_dataset()
    print(f"[load] CAR 計算可能 {len(rdf)} 件")

    names = load_price_targets_names()

    make_concept(rdf)
    print("[ok] 01_car_concept.png")
    make_category_car(rdf)
    print("[ok] 02_category_car.png")
    make_scatter(rdf)
    print("[ok] 03_surprise_scatter.png")
    make_periods(rdf)
    print("[ok] 04_periods_comparison.png")
    make_top_bottom(rdf, names)
    print("[ok] 05_top_bottom_cases.png")
