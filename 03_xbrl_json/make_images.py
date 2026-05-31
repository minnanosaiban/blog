"""
blog/06_XBRLとは何か.md 用の画像生成スクリプト。

生成画像:
  01_oil_3companies_revenue_oi.png  — 石油元売 3 社の売上 / 営業利益 7 年推移
  02_oil_3companies_ni_roe.png      — 3 社の純利益 / ROE 7 年推移
  03_oil_3companies_cf.png          — 3 社の CF 3 種（営業/投資/財務）7 年推移
  04_data_depth_comparison.png      — 既存スクリーナー vs XBRL データ深度比較
  05_eneos_peakout.png              — ＥＮＥＯＳ 単独の 2022 ピークアウト構図

実行: python scripts/blog/03_xbrl_to_json_make_images.py
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
from matplotlib.patches import Rectangle


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

C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/03_xbrl_to_json")
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
    ("E31632", "コスモエネＨＤ", "#5a9a72"),  # 緑（CFチャートと共通）
    ("E24050", "ＥＮＥＯＳ",      "#3498db"),  # 青
    ("E01084", "出光興産",       "#c87878"),  # 赤
]


def load_oil_series() -> pd.DataFrame:
    rows = []
    for ed, name, color in OIL_3:
        for f in sorted((YUHO / ed).glob("*.json")):
            with open(f, encoding="utf-8") as fp:
                d = json.load(fp)
            fy = d.get("metadata", {}).get("fiscal_year_end", "")
            fin = d.get("financials", {}) or {}
            rows.append({
                "name": name, "color": color,
                "fy": fy[:4],
                "net_sales": fin.get("net_sales"),
                "net_income": fin.get("net_income"),
                "roe": fin.get("roe"),
                "equity_ratio": fin.get("equity_ratio"),
                "total_assets": fin.get("total_assets"),
                "op_cf": fin.get("operating_cf"),
                "inv_cf": fin.get("investing_cf"),
                "fin_cf": fin.get("financing_cf"),
            })
    return pd.DataFrame(rows)


# ── 1) 売上高 / 自己資本比率 7 年 ─────────────────────────────────────────
def make_revenue(df: pd.DataFrame) -> None:
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13, 5.5),
                                     gridspec_kw=dict(wspace=0.28))
    fig.subplots_adjust(top=0.80)

    # 左: 売上高（規模）
    for _, name, color in OIL_3:
        sub = df[df["name"] == name].sort_values("fy")
        ax_l.plot(sub["fy"], sub["net_sales"] / 1e12,
                  marker="o", markersize=7, linewidth=2.4, color=color, label=name)
    ax_l.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax_l.set_ylabel("売上高（兆円）", fontsize=16, color=C_TEXT)
    ax_l.set_title("売上高 7 年推移", fontsize=16, fontweight="bold",
                   color=C_TEXT, pad=24, loc="left")
    ax_l.legend(loc="best", fontsize=15, frameon=False)
    ax_l.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)

    # 右: 自己資本比率（財務体質）
    for _, name, color in OIL_3:
        sub = df[df["name"] == name].sort_values("fy")
        ax_r.plot(sub["fy"], sub["equity_ratio"] * 100,
                  marker="o", markersize=7, linewidth=2.4, color=color, label=name)
    ax_r.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_ylabel("自己資本比率（%）", fontsize=16, color=C_TEXT)
    ax_r.set_title("自己資本比率 7 年推移", fontsize=16, fontweight="bold",
                   color=C_TEXT, pad=24, loc="left")
    ax_r.legend(loc="best", fontsize=15, frameon=False)
    ax_r.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)

    fig.suptitle("石油元売 3 社  ―  有報 XBRL からの 7 年時系列",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=0.98)
    _savefig_vpad(fig, OUT_DIR / "01_oil_3companies_revenue.png")
    plt.close(fig)


# ── 2) 純利益 / ROE 7 年 ──────────────────────────────────────────────────
def make_ni_roe(df: pd.DataFrame) -> None:
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13, 6),
                                     gridspec_kw=dict(wspace=0.28))
    fig.subplots_adjust(top=0.80)

    for _, name, color in OIL_3:
        sub = df[df["name"] == name].sort_values("fy")
        ax_l.plot(sub["fy"], sub["net_income"] / 1e11,
                  marker="o", markersize=7, linewidth=2.2,
                  color=color, label=name)

    ax_l.axhline(0, color="#999999", linewidth=0.8)
    ax_l.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax_l.set_ylabel("純利益（千億円）", fontsize=16, color=C_TEXT)
    ax_l.set_title("純利益 7 年推移",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax_l.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_ylim(-2.6, 6.0)

    # 3 社とも 2022 がピーク。各ピークに白丸を打ち、右上にまとめて表示
    peaks = []
    for _, name, color in OIL_3:
        sub = df[df["name"] == name].sort_values("fy")
        if sub.empty:
            continue
        peak_row = sub.loc[sub["net_income"].idxmax()]
        ax_l.scatter(peak_row["fy"], peak_row["net_income"] / 1e11,
                     s=120, edgecolor=color, facecolor="white",
                     linewidth=2.5, zorder=5)
        peaks.append((name, peak_row["net_income"] / 1e11, color))

    ax_l.text(0.96, 0.97, "2022 がピーク", transform=ax_l.transAxes,
              ha="right", va="top", fontsize=15, fontweight="bold", color=C_TEXT_SUB)
    for i, (name, val, color) in enumerate(sorted(peaks, key=lambda t: -t[1])):
        ax_l.text(0.96, 0.88 - i * 0.085, f"{name}  {val:.1f}千億",
                  transform=ax_l.transAxes, ha="right", va="top",
                  fontsize=15, fontweight="bold", color=color)

    # ROE（赤字の 2020 など報告 ROE 欠損年は 純利益÷自己資本 で補完し線を連続させる）
    for _, name, color in OIL_3:
        sub = df[df["name"] == name].sort_values("fy")
        equity = sub["total_assets"] * sub["equity_ratio"]
        roe_pct = sub["roe"].fillna(sub["net_income"] / equity) * 100
        ax_r.plot(sub["fy"], roe_pct,
                  marker="o", markersize=7, linewidth=2.2,
                  color=color, label=name)

    ax_r.axhline(0, color="#999999", linewidth=0.8)
    ax_r.axhline(10, color="#999999", linestyle=":", linewidth=0.9, alpha=0.8,
                 label="ROE 10% (優良ライン)")
    ax_r.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_ylabel("ROE（%）", fontsize=16, color=C_TEXT)
    ax_r.set_title("ROE 7 年推移",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax_r.legend(loc="lower right", fontsize=14, frameon=False)
    ax_r.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)

    fig.suptitle("石油元売 3 社  ―  2022 利益ピークと直近のピークアウト構図",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=0.98)
    _savefig_vpad(fig, OUT_DIR / "02_oil_3companies_ni_roe.png")
    plt.close(fig)


# ── 3) CF 3 種 7 年 ──────────────────────────────────────────────────────
def make_cf(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5),
                             gridspec_kw=dict(wspace=0.3))

    for ax, (_, name, color) in zip(axes, OIL_3):
        sub = df[df["name"] == name].sort_values("fy")
        x = sub["fy"].values
        op = sub["op_cf"].values / 1e11
        inv = sub["inv_cf"].values / 1e11
        fin = sub["fin_cf"].values / 1e11

        bw = 0.27
        idx = np.arange(len(x))
        ax.bar(idx - bw, op, width=bw, color="#5a9a72", alpha=0.85,
               edgecolor="white", linewidth=0.8, label="営業CF")
        ax.bar(idx,      inv, width=bw, color="#c87878", alpha=0.85,
               edgecolor="white", linewidth=0.8, label="投資CF")
        ax.bar(idx + bw, fin, width=bw, color="#3498db", alpha=0.85,
               edgecolor="white", linewidth=0.8, label="財務CF")

        ax.axhline(0, color="#444444", linewidth=0.8)
        ax.set_xticks(idx)
        ax.set_xticklabels(x, fontsize=14, rotation=45, ha="right")
        ax.set_ylabel("CF（千億円）" if ax is axes[0] else "",
                      fontsize=16, color=C_TEXT_SUB)
        ax.text(0.5, 0.97, f"{name}", fontsize=16, fontweight="bold",
                color=C_TEXT, transform=ax.transAxes, ha="center", va="top")
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3,
               fontsize=14, frameon=False,
               bbox_to_anchor=(0.5, 1.04))

    fig.suptitle("キャッシュフロー 3 種の 7 年推移  ―  投資フェーズの可視化",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.12)
    _savefig_vpad(fig, OUT_DIR / "03_oil_3companies_cf.png")
    plt.close(fig)


# ── 4) データ深度比較 ──────────────────────────────────────────────────────
def make_data_depth() -> None:
    """既存スクリーナー vs XBRL のデータ深度を視覚化（カバレッジテーブル風）"""
    categories = [
        ("ROE / PER / PBR", [1, 1, 1, 1]),
        ("EPS / 配当 / 売上", [1, 1, 1, 1]),
        ("業績予想修正率", [1, 0, 1, 1]),
        ("信用残・出来高", [1, 0, 0, 1]),
        ("セグメント別売上・利益", [0, 0.4, 0, 1]),
        ("地域別売上", [0, 0.4, 0, 1]),
        ("減価償却・設備投資", [0, 0.6, 0, 1]),
        ("運転資本（売掛・在庫）", [0, 0.6, 0, 1]),
        ("キャッシュフロー詳細", [0, 0.6, 0, 1]),
        ("注記・会計方針変更", [0, 0, 0, 1]),
        ("経営方針テキスト", [0, 0, 0, 1]),
        ("過去 7 年超の時系列", [0, 0.6, 0.6, 1]),
    ]
    sources = ["証券会社系\n（市販A）", "無料Web系\n（市販B）", "有料Web系\n（市販C）", "自前 XBRL\n→ JSON"]

    arr = np.array([row[1] for row in categories])
    labels = [row[0] for row in categories]

    fig, ax = plt.subplots(figsize=(11, 7))

    CELL_COLORS = {0: "#eeeeee", 0.4: "#cde0f5", 0.6: "#93bfe0", 1: "#3a7ebf"}
    TEXT_COLORS = {0: "#999999", 0.4: "#404040", 0.6: "#202124", 1: "white"}
    for i, lab in enumerate(labels):
        for j, src in enumerate(sources):
            v = arr[i, j]
            color = CELL_COLORS.get(v, "#eeeeee")
            rect = Rectangle((j, len(labels) - i - 1), 1, 1,
                             facecolor=color, edgecolor="white", linewidth=1.5)
            ax.add_patch(rect)
            if v == 0:
                txt = "—"; tc = TEXT_COLORS[0]
            elif v < 0.5:
                txt = "△"; tc = TEXT_COLORS[0.4]
            elif v < 0.8:
                txt = "△+"; tc = TEXT_COLORS[0.6]
            else:
                txt = "✓"; tc = TEXT_COLORS[1]
            ax.text(j + 0.5, len(labels) - i - 0.5, txt,
                    fontsize=16, ha="center", va="center",
                    color=tc, fontweight="bold")

    ax.set_xlim(0, len(sources))
    ax.set_ylim(0, len(labels))
    ax.set_xticks(np.arange(len(sources)) + 0.5)
    ax.set_xticklabels(sources, fontsize=16, color=C_TEXT)
    ax.set_yticks(np.arange(len(labels)) + 0.5)
    ax.set_yticklabels(labels[::-1], fontsize=16, color=C_TEXT)
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)

    ax.set_title("データ深度比較  ―  既存サービスと自前 XBRL の到達範囲",
                 fontsize=16, fontweight="bold", color=C_TEXT,
                 pad=42, loc="left")

    fig.text(0.5, -0.02,
             "✓ 完全提供  /  △+ 部分提供  /  △ 限定的  /  — 提供なし",
             fontsize=16, color=C_TEXT_SUB, ha="center")
    _savefig_vpad(fig, OUT_DIR / "04_data_depth_comparison.png")
    plt.close(fig)


# ── 5) ＥＮＥＯＳ 単独の 2022 ピークアウト ──────────────────────────────────
def make_eneos_peakout(df: pd.DataFrame) -> None:
    sub = df[df["name"] == "ＥＮＥＯＳ"].sort_values("fy").reset_index(drop=True)

    fig, ax_ni = plt.subplots(figsize=(13, 5.5))
    ax_roe = ax_ni.twinx()

    x = sub["fy"]
    ni = sub["net_income"] / 1e11
    roe = sub["roe"] * 100

    # 純利益（バー）
    colors = ["#c87878" if v < 0 else "#5a9a72" for v in ni]
    bars = ax_ni.bar(x, ni, color=colors, alpha=0.7,
                     edgecolor="white", linewidth=1.0,
                     label="純利益（千億円、左軸）")
    for xi, v in zip(x, ni):
        ax_ni.text(xi, v + (0.2 if v >= 0 else -0.4), f"{v:.1f}",
                   ha="center", va="bottom" if v >= 0 else "top",
                   fontsize=16, fontweight="bold",
                   color="#5a9a72" if v >= 0 else "#c87878")

    # ROE（ライン）
    ax_roe.plot(x, roe, marker="o", markersize=8, linewidth=2.5,
                color="#888888", label="ROE（%、右軸）")
    for xi, v in zip(x, roe):
        ax_roe.text(xi, v + 0.6, f"{v:.1f}%",
                    ha="center", va="bottom",
                    fontsize=16, color="#888888", fontweight="bold")

    # ピーク注釈
    peak_idx = sub["net_income"].idxmax()
    peak_row = sub.iloc[peak_idx]
    ax_ni.annotate(
        f"2022 ピーク\n純利益 5,371 億円 / ROE 20.7%",
        xy=(peak_row["fy"], peak_row["net_income"] / 1e11),
        xytext=(2, 4.5), textcoords="data",
        fontsize=16, color="#c87878", fontweight="bold",
        ha="center",
        arrowprops=dict(arrowstyle="->", color="#c87878", lw=1.5),
    )

    ax_ni.axhline(0, color="#999999", linewidth=0.8)
    ax_ni.set_ylabel("純利益（千億円）", fontsize=16, color="#3498db")
    ax_roe.set_ylabel("ROE（%）", fontsize=16, color="#888888")
    ax_ni.set_xlabel("会計年度", fontsize=16, color=C_TEXT_SUB)
    ax_ni.set_ylim(-3.5, 7.5)
    ax_roe.set_ylim(-12, 25)
    ax_ni.tick_params(axis="y", colors="#3498db")
    ax_roe.tick_params(axis="y", colors="#888888")
    ax_ni.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top",):
        ax_ni.spines[sp].set_visible(False)
        ax_roe.spines[sp].set_visible(False)

    ax_ni.set_title("ＥＮＥＯＳ  ―  2022 ピークから 2025 へのピークアウト構図",
                    fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    ax_ni.legend(loc="upper left", fontsize=16, frameon=False)
    ax_roe.legend(loc="upper right", fontsize=16, frameon=False)

    _savefig_vpad(fig, OUT_DIR / "05_eneos_peakout.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_oil_series()
    print(f"[load] {len(df)} 行（{df['name'].nunique()} 社 × 7 期）")

    make_revenue(df)
    print("[ok] 01_oil_3companies_revenue.png")
    make_ni_roe(df)
    print("[ok] 02_oil_3companies_ni_roe.png")
    make_cf(df)
    print("[ok] 03_oil_3companies_cf.png")
    make_data_depth()
    print("[ok] 04_data_depth_comparison.png")
    make_eneos_peakout(df)
    print("[ok] 05_eneos_peakout.png")

    print("\n=== ＥＮＥＯＳ 7 年 純利益・ROE ===")
    sub = df[df["name"] == "ＥＮＥＯＳ"].sort_values("fy")
    for _, r in sub.iterrows():
        print(f"  {r['fy']}: 純利={r['net_income']/1e8:,.0f}億 / ROE={r['roe']*100:.1f}%")
