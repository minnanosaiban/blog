"""
blog/10_アクルーアル.md 用の画像生成スクリプト。

生成画像:
  01_oil_3_accrual_timeline.png — 石油元売 3 社のアクルーアル 7 年推移
  02_oil_3_ni_vs_cf.png         — 純利益 vs 営業 CF の年次対比（45 度線基準）
  03_13_companies_rank.png      — 13 社の 7 年平均アクルーアル ランキング
  04_ni_cf_scatter.png          — 91 サンプルの純利益 × 営業CF 散布図
  05_eneos_quality.png          — ENEOS の 2022 ピーク利益の質を可視化

実行: python scripts/blog/09_accrual_analysis_make_images.py
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

C_HEALTHY = "#5a9a72"
C_WARN    = "#c87878"
C_NEUTRAL = "#999999"
C_NI      = "#3498db"
C_CF      = "#5a9a72"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/09_accrual_analysis")
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


YUHO = Path(r"C:/stock_analysis/data/yuho")

OIL_3 = [
    ("E31632", "コスモエネＨＤ", "#888888"),
    ("E24050", "ＥＮＥＯＳ",      "#444444"),
    ("E01084", "出光興産",       "#aaaaaa"),
]


def load_yuho_all() -> pd.DataFrame:
    """全 EDINET 銘柄の有報 JSON を読み込み、アクルーアル指標を計算。"""
    em_path = Path("C:/stock_analysis/data/master/edinet_map.json")
    em = json.load(open(em_path, encoding="utf-8"))
    inv_em = {v: k for k, v in em.items()}

    rows = []
    for ed_dir in YUHO.iterdir():
        if not ed_dir.is_dir():
            continue
        ed = ed_dir.name
        code = inv_em.get(ed, "???")
        for f in sorted(ed_dir.glob("*.json")):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            meta = d.get("metadata", {})
            fin = d.get("financials", {}) or {}
            rows.append({
                "edinet": ed,
                "code": code,
                "name": meta.get("company_name", ""),
                "fy_end": meta.get("fiscal_year_end", ""),
                "fy": meta.get("fiscal_year_end", "")[:4],
                "std": meta.get("accounting_standard", ""),
                "net_income": fin.get("net_income"),
                "op_cf": fin.get("operating_cf"),
                "inv_cf": fin.get("investing_cf"),
                "total_assets": fin.get("total_assets"),
                "net_sales": fin.get("net_sales"),
                "roe": fin.get("roe"),
            })

    df = pd.DataFrame(rows)
    # アクルーアル比率 = (純利益 - 営業CF) / 総資産
    df["accrual"] = (df["net_income"] - df["op_cf"]) / df["total_assets"]
    # CF/純利益（補助指標、純利益 ≈ 0 で発散するので NaN 化）
    df["cf_ni_ratio"] = df["op_cf"] / df["net_income"].where(df["net_income"].abs() >= 1e9)
    return df


# ── 1) 石油元売 3 社のアクルーアル 7 年推移 ────────────────────────────────
def make_oil_accrual_timeline(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 6))

    for ed, name, color in OIL_3:
        sub = df[df["edinet"] == ed].sort_values("fy")
        ax.plot(sub["fy"], sub["accrual"], marker="o", markersize=8,
                linewidth=2.2, color=color, label=name)

    # ゾーン背景
    ax.axhspan(-0.20, -0.05, facecolor=C_HEALTHY, alpha=0.08)
    ax.axhspan(-0.05, 0.05, facecolor="#aaaaaa", alpha=0.04)
    ax.axhspan(0.05, 0.10, facecolor="#F39C12", alpha=0.08)
    ax.axhspan(0.10, 0.30, facecolor=C_WARN, alpha=0.08)

    # ゾーンラベル
    ax.text(6.3, -0.08, "★低アクルーアル\n（健全）", fontsize=16, color=C_HEALTHY,
            ha="left", va="center", fontweight="bold")
    ax.text(6.3, 0.07, "警戒", fontsize=16, color="#aaaaaa",
            ha="left", va="center", fontweight="bold")
    ax.text(6.3, 0.0, "普通", fontsize=16, color="#888888",
            ha="left", va="center")

    ax.axhline(0, color="#999999", linewidth=0.7)
    ax.axhline(-0.05, color=C_HEALTHY, linewidth=0.6, linestyle="--", alpha=0.5)
    ax.axhline(0.05, color="#aaaaaa", linewidth=0.6, linestyle="--", alpha=0.5)

    # ENEOS 2022 を強調
    eneos = df[df["edinet"] == "E24050"]
    p22 = eneos[eneos["fy"] == "2022"]
    if not p22.empty:
        r = p22.iloc[0]
        ax.annotate(
            "ＥＮＥＯＳ 2022\nピーク純利益 5,371 億円\nだが CF/純利 0.39",
            xy=("2022", r["accrual"]),
            xytext=(0.5, 0.18), textcoords="data",
            fontsize=16, color=C_TEXT, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_TEXT, lw=1.5),
            bbox=dict(facecolor="white", edgecolor="#aaaaaa",
                      boxstyle="round,pad=0.3"),
        )

    ax.set_xlim(-0.5, 7.5)
    ax.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax.set_ylabel("アクルーアル比率（純利益 − 営業CF）÷ 総資産",
                  fontsize=16, color=C_TEXT)
    ax.set_title("石油元売 3 社  ―  アクルーアル比率 7 年推移",
                 fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax.legend(loc="lower left", fontsize=16, frameon=False)
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    _savefig_vpad(fig, OUT_DIR / "01_oil_3_accrual_timeline.png")
    plt.close(fig)


# ── 2) 純利益 vs 営業CF 年次対比 ─────────────────────────────────────────────
def make_oil_ni_vs_cf(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2),
                             gridspec_kw=dict(wspace=0.32))
    fig.subplots_adjust(top=0.88)

    for ax, (ed, name, color) in zip(axes, OIL_3):
        sub = df[df["edinet"] == ed].sort_values("fy")
        x = np.arange(len(sub))
        bw = 0.38

        ni = sub["net_income"].values / 1e11
        cf = sub["op_cf"].values / 1e11

        ax.bar(x - bw / 2, ni, width=bw, color=C_NI, alpha=0.85,
               edgecolor="white", linewidth=0.8, label="純利益")
        ax.bar(x + bw / 2, cf, width=bw, color=C_CF, alpha=0.85,
               edgecolor="white", linewidth=0.8, label="営業CF")

        for xi, v in zip(x - bw / 2, ni):
            ax.text(xi, v + (0.2 if v >= 0 else -0.4), f"{v:.1f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=16, color=C_NI, fontweight="bold")
        for xi, v in zip(x + bw / 2, cf):
            ax.text(xi, v + (0.2 if v >= 0 else -0.4), f"{v:.1f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=16, color=C_CF, fontweight="bold")

        # 2022 ピーク年を強調枠
        if "2022" in sub["fy"].values:
            i22 = list(sub["fy"]).index("2022")
            ax.axvspan(i22 - 0.5, i22 + 0.5, facecolor="#c87878", alpha=0.06)

        ax.axhline(0, color="#444444", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(sub["fy"].values, fontsize=16)
        ax.set_ylabel("（千億円）" if ax is axes[0] else "",
                      fontsize=16, color=C_TEXT_SUB)
        ylo, yhi = ax.get_ylim()
        ax.set_ylim(ylo, yhi * 1.28)
        ax.text(0.5, 0.97, name, fontsize=16, fontweight="bold",
                color=color, transform=ax.transAxes, ha="center", va="top")
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2,
               fontsize=14, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("純利益 vs 営業CF の 7 年対比  ―  2022 ピーク年は赤帯",
                 fontsize=20, fontweight="bold", color=C_TEXT, y=1.12)
    _savefig_vpad(fig, OUT_DIR / "02_oil_3_ni_vs_cf.png")
    plt.close(fig)


# ── 3) 13 社の 7 年平均アクルーアル ランキング ────────────────────────────────
def make_13_companies_rank(df: pd.DataFrame) -> None:
    gp = (df.dropna(subset=["accrual"])
          .groupby(["edinet", "name"])
          .agg(mean_accrual=("accrual", "mean"),
               std_accrual=("accrual", "std"),
               n_years=("accrual", "count"))
          .reset_index())

    # 同一銘柄の name 差分を吸収（ENEOS は途中で表記が変わったため）
    # EDINET 単位で集計し直す
    gp = (df.dropna(subset=["accrual"])
          .groupby("edinet")
          .agg(mean_accrual=("accrual", "mean"),
               std_accrual=("accrual", "std"),
               n_years=("accrual", "count"))
          .reset_index())

    # EDINET → 銘柄名（最後の表記を採用）
    edinet_to_name = {}
    edinet_to_code = {}
    for ed, gdf in df.groupby("edinet"):
        latest = gdf.sort_values("fy_end").iloc[-1]
        edinet_to_name[ed] = latest["name"][:14]
        edinet_to_code[ed] = latest["code"]

    gp["name"] = gp["edinet"].map(edinet_to_name)
    gp["code"] = gp["edinet"].map(edinet_to_code)
    gp = gp.sort_values("mean_accrual")

    fig, ax = plt.subplots(figsize=(13, 7))
    y = np.arange(len(gp))
    colors = [C_HEALTHY if v <= -0.05 else
              "#85c1e9" if v <= 0 else
              "#F39C12" if v <= 0.05 else C_WARN
              for v in gp["mean_accrual"]]

    ax.barh(y, gp["mean_accrual"], color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    # 標準偏差をエラーバーで
    ax.errorbar(gp["mean_accrual"], y,
                xerr=gp["std_accrual"], fmt="none",
                ecolor="#444444", alpha=0.4, capsize=3)

    for i, (_, r) in enumerate(gp.iterrows()):
        label = f"{r['mean_accrual']:+.3f}  (σ {r['std_accrual']:.3f}, n={r['n_years']})"
        ax.text(r["mean_accrual"] - 0.003, i, label,
                va="center", ha="right",
                fontsize=16, color=C_TEXT, fontweight="bold")

    # 石油元売 3 社ハイライト
    oil_edinets = {ed for ed, _, _ in OIL_3}
    for i, ed in enumerate(gp["edinet"]):
        face = "#1F4E8C" if ed in oil_edinets else None
        if face:
            ax.add_patch(plt.Rectangle((-0.1, i - 0.4), 0.005, 0.8,
                                       color=face, clip_on=False, zorder=3))

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name']}"
                        for _, r in gp.iterrows()], fontsize=16)
    ax.axvline(-0.05, color=C_HEALTHY, linestyle="--", linewidth=0.7)
    ax.axvline(0, color="#999999", linewidth=0.7)
    ax.axvline(0.05, color="#F39C12", linestyle="--", linewidth=0.7)
    ax.set_xlim(-0.11, 0.04)
    ax.set_xlabel("平均アクルーアル比率（誤差バー = 標準偏差）",
                  fontsize=16, color=C_TEXT)
    ax.set_title("13 社の 7 年平均アクルーアル ランキング  ―  全社が健全圏",
                 fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

    fig.text(0.05, -0.02,
             "青棒 = 石油元売 3 社。商社・エネルギー業界は構造的に低アクルーアル（健全）",
             fontsize=16, color=C_TEXT_SUB, style="italic")
    _savefig_vpad(fig, OUT_DIR / "03_13_companies_rank.png")
    plt.close(fig)


# ── 4) 純利益 × 営業CF 散布図 ────────────────────────────────────────────────
def make_ni_cf_scatter(df: pd.DataFrame) -> None:
    sub = df.dropna(subset=["net_income", "op_cf", "total_assets"]).copy()
    sub["ni_normalized"] = sub["net_income"] / sub["total_assets"] * 100
    sub["cf_normalized"] = sub["op_cf"] / sub["total_assets"] * 100

    fig, ax = plt.subplots(figsize=(13, 7.5))

    # 45 度線（純利益 = 営業CF）
    lo = min(sub["ni_normalized"].min(), sub["cf_normalized"].min()) * 1.05
    hi = max(sub["ni_normalized"].max(), sub["cf_normalized"].max()) * 1.05
    lo = max(lo, -8)
    hi = min(hi, 14)

    ax.plot([lo, hi], [lo, hi], color="#666666", linestyle="--", linewidth=1.0,
            alpha=0.6, label="45° 線（純利益 = 営業CF）")

    # 健全領域（CF が純利益より大きい = 線上）
    xx = np.linspace(lo, hi, 50)
    ax.fill_between(xx, xx, hi, color=C_HEALTHY, alpha=0.05)
    ax.fill_between(xx, lo, xx, color=C_WARN, alpha=0.04)

    # 全銘柄
    is_oil = sub["edinet"].isin([ed for ed, _, _ in OIL_3])
    bg = sub[~is_oil]
    ax.scatter(bg["ni_normalized"], bg["cf_normalized"],
               s=40, color="#aaaaaa", alpha=0.55, edgecolors="white",
               linewidth=0.4, label=f"その他 10 社 ({len(bg)} 件)")

    # 石油元売 3 社
    for ed, name, color in OIL_3:
        oil_sub = sub[sub["edinet"] == ed]
        ax.scatter(oil_sub["ni_normalized"], oil_sub["cf_normalized"],
                   s=110, color=color, alpha=0.85,
                   edgecolors="white", linewidth=1.0, label=name, zorder=5)

    # ENEOS 2022 を星マークで強調
    e22 = sub[(sub["edinet"] == "E24050") & (sub["fy"] == "2022")]
    if not e22.empty:
        r = e22.iloc[0]
        ax.scatter(r["ni_normalized"], r["cf_normalized"], s=400,
                   marker="*", color=C_TEXT, edgecolors="white",
                   linewidth=2.0, zorder=10)
        ax.annotate("ＥＮＥＯＳ 2022\n（CF が純利益の 39%）",
                    xy=(r["ni_normalized"], r["cf_normalized"]),
                    xytext=(20, -30), textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    arrowprops=dict(arrowstyle="->", color=C_TEXT, lw=1.5),
                    bbox=dict(facecolor="white", edgecolor="#aaaaaa",
                              boxstyle="round,pad=0.3"))

    # ゾーンラベル
    ax.text(hi * 0.6, hi * 0.85, "★健全\n（CF > 純利益）",
            fontsize=16, fontweight="bold", color=C_HEALTHY,
            ha="center", va="center")
    ax.text(hi * 0.7, lo * 0.55, "警戒\n（純利益 > CF）",
            fontsize=16, fontweight="bold", color=C_WARN,
            ha="center", va="center")

    ax.axhline(0, color="#777777", linewidth=0.7)
    ax.axvline(0, color="#777777", linewidth=0.7)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("純利益 ÷ 総資産 × 100（％）",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("営業CF ÷ 総資産 × 100（％）",
                  fontsize=16, color=C_TEXT)
    ax.set_title(
        "純利益 × 営業CF 散布図  ―  13 社 × 7 期 = 91 サンプル",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    ax.legend(loc="upper left", fontsize=16, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    _savefig_vpad(fig, OUT_DIR / "04_ni_cf_scatter.png")
    plt.close(fig)


# ── 5) ＥＮＥＯＳ の利益の質ハイライト ────────────────────────────────────────
def make_eneos_quality(df: pd.DataFrame) -> None:
    sub = df[df["edinet"] == "E24050"].sort_values("fy").reset_index(drop=True)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12, 7.5),
                                          gridspec_kw=dict(height_ratios=[1.4, 1],
                                                            hspace=0.3))

    x = np.arange(len(sub))
    bw = 0.35

    # 上段: 純利益 vs 営業CF
    ni = sub["net_income"] / 1e11
    cf = sub["op_cf"] / 1e11
    ax_top.bar(x - bw / 2, ni, width=bw, color=C_NI, alpha=0.85,
               edgecolor="white", linewidth=0.8, label="純利益")
    ax_top.bar(x + bw / 2, cf, width=bw, color=C_CF, alpha=0.85,
               edgecolor="white", linewidth=0.8, label="営業CF")
    for xi, v in zip(x - bw / 2, ni):
        ax_top.text(xi, v + (0.2 if v >= 0 else -0.4), f"{v:.1f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=16, color=C_NI, fontweight="bold")
    for xi, v in zip(x + bw / 2, cf):
        ax_top.text(xi, v + (0.2 if v >= 0 else -0.4), f"{v:.1f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=16, color=C_CF, fontweight="bold")

    # 2022 ピーク年を強調
    i22 = list(sub["fy"]).index("2022")
    ax_top.axvspan(i22 - 0.55, i22 + 0.55, facecolor="#c87878", alpha=0.08)
    ax_top.annotate(
        "2022 ピーク年\n純利益 5,371 億円のうち\nCF 化は 2,095 億円 (39%)",
        xy=(i22, ni.iloc[i22]),
        xytext=(i22 - 1.8, 7.0), textcoords="data",
        fontsize=16, fontweight="bold", color="#c87878", ha="center",
        arrowprops=dict(arrowstyle="->", color="#c87878", lw=1.5),
        bbox=dict(facecolor="white", edgecolor="#c87878", boxstyle="round,pad=0.3"),
    )

    ax_top.axhline(0, color="#444444", linewidth=0.8)
    ax_top.set_xticks(x)
    ax_top.set_xticklabels(sub["fy"].values, fontsize=16)
    ax_top.set_ylabel("純利益・営業CF（千億円）",
                      fontsize=16, color=C_TEXT)
    ax_top.set_title("ＥＮＥＯＳ  ―  2022 ピーク利益はキャッシュで裏付けられていなかった",
                     fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax_top.legend(loc="upper left", fontsize=16, frameon=False)
    ax_top.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_top.spines[sp].set_visible(False)

    # 下段: アクルーアル比率
    accr = sub["accrual"].values
    colors_bar = [C_WARN if v > 0.02 else
                  "#F39C12" if v > 0 else
                  C_HEALTHY if v < -0.05 else "#85c1e9"
                  for v in accr]
    ax_bot.bar(x, accr, color=colors_bar, alpha=0.85,
               edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, accr):
        if pd.notna(v):
            ax_bot.text(xi, v + (0.003 if v >= 0 else -0.004),
                        f"{v:+.3f}", ha="center",
                        va="bottom" if v >= 0 else "top",
                        fontsize=16, color=C_TEXT, fontweight="bold")

    ax_bot.axhline(0, color="#444444", linewidth=0.8)
    ax_bot.axhline(-0.05, color=C_HEALTHY, linestyle="--",
                   linewidth=0.7, alpha=0.7)
    ax_bot.axhline(0.05, color="#F39C12", linestyle="--",
                   linewidth=0.7, alpha=0.7)
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(sub["fy"].values, fontsize=16)
    ax_bot.set_ylabel("アクルーアル比率", fontsize=16, color=C_TEXT)
    ax_bot.set_title("同年のアクルーアル比率（プラス = 純利益が CF を超過 = 警戒寄り）",
                     fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax_bot.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_bot.spines[sp].set_visible(False)

    _savefig_vpad(fig, OUT_DIR / "05_eneos_quality.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_yuho_all()
    print(f"[load] {len(df)} 行 / {df['edinet'].nunique()} EDINET 銘柄")

    make_oil_accrual_timeline(df)
    print("[ok] 01_oil_3_accrual_timeline.png")
    make_oil_ni_vs_cf(df)
    print("[ok] 02_oil_3_ni_vs_cf.png")
    make_13_companies_rank(df)
    print("[ok] 03_13_companies_rank.png")
    make_ni_cf_scatter(df)
    print("[ok] 04_ni_cf_scatter.png")
    make_eneos_quality(df)
    print("[ok] 05_eneos_quality.png")
