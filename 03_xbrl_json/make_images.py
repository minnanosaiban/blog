"""
連載03 用の画像生成スクリプト ― 石油元売 3 社の有報 XBRL 7 年時系列。

生成画像（OUT_DIR に出力）:
  01_oil_3companies_revenue.png     — 売上高 / 自己資本比率 7 年推移
  02_oil_3companies_ni_roe.png      — 純利益 / ROE 7 年推移
  03_oil_3companies_cf.png          — CF 3 種（営業 / 投資 / 財務）7 年推移

入力: data/yuho/{EDINETコード}/*.json（有報 XBRL → JSON 変換の出力）
      ※ 有報 JSON は提供元の規約により再配布できません。
        EDINET から取得し、ご自身の環境で生成してください（data/ は空のプレースホルダ）。

実行: python make_images.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# ── パス（スクリプト基準の相対パス）────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data" / "yuho"
OUT_DIR  = Path(__file__).parent / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── デザイン設定 ────────────────────────────────────────────────────────────
mpl.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP"]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["figure.facecolor"] = "white"
mpl.rcParams["axes.facecolor"] = "white"
mpl.rcParams["savefig.facecolor"] = "white"
mpl.rcParams["savefig.bbox"] = "tight"
mpl.rcParams["savefig.dpi"] = 144
mpl.rcParams["font.size"] = 16
mpl.rcParams["axes.titlesize"] = 20
mpl.rcParams["axes.labelsize"] = 16
mpl.rcParams["xtick.labelsize"] = 16
mpl.rcParams["ytick.labelsize"] = 16
mpl.rcParams["legend.fontsize"] = 16

C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

# 石油元売 3 社（EDINET コード, 表示名, 線色）
OIL_3 = [
    ("E31632", "コスモエネＨＤ", "#5a9a72"),  # 緑（CFチャートと共通）
    ("E24050", "ＥＮＥＯＳ",      "#3498db"),  # 青
    ("E01084", "出光興産",       "#c87878"),  # 赤
]


def _savefig_vpad(fig: plt.Figure, path: Path, bpad: float = 0.5) -> None:
    """下のみ bpad インチの余白を追加して保存する（上・左右は余白なし）。"""
    import io
    buf = io.BytesIO()
    fig.savefig(buf, bbox_inches="tight", pad_inches=0, format="png")
    buf.seek(0)
    img = plt.imread(buf)
    pad_rows = max(1, round(bpad * fig.dpi))
    white = np.ones((pad_rows, img.shape[1], img.shape[2]), dtype=img.dtype)
    plt.imsave(str(path), np.vstack([img, white]), dpi=fig.dpi)


def load_oil_series() -> pd.DataFrame:
    """3 社分の有報 JSON を読み、7 期の業績指標を 1 つの DataFrame にまとめる。"""
    rows = []
    for ed, name, color in OIL_3:
        for f in sorted((DATA_DIR / ed).glob("*.json")):
            with open(f, encoding="utf-8") as fp:
                d = json.load(fp)
            fy = d.get("metadata", {}).get("fiscal_year_end", "")
            fin = d.get("financials", {}) or {}
            rows.append({
                "name": name, "color": color, "fy": fy[:4],
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
                  marker="o", markersize=7, linewidth=2.2, color=color, label=name)

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
                  marker="o", markersize=7, linewidth=2.2, color=color, label=name)

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
               fontsize=14, frameon=False, bbox_to_anchor=(0.5, 1.04))

    fig.suptitle("キャッシュフロー 3 種の 7 年推移  ―  投資フェーズの可視化",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.12)
    _savefig_vpad(fig, OUT_DIR / "03_oil_3companies_cf.png")
    plt.close(fig)


if __name__ == "__main__":
    df = load_oil_series()
    if df.empty:
        raise SystemExit(
            "data/yuho/ に有報 JSON がありません。EDINET から取得し、"
            "XBRL → JSON 変換の出力を data/yuho/{EDINETコード}/ に配置してください。"
        )
    print(f"[load] {len(df)} 行（{df['name'].nunique()} 社 × {df['fy'].nunique()} 期）")

    make_revenue(df)
    print("[ok] 01_oil_3companies_revenue.png")
    make_ni_roe(df)
    print("[ok] 02_oil_3companies_ni_roe.png")
    make_cf(df)
    print("[ok] 03_oil_3companies_cf.png")
