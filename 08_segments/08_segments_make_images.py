"""
blog/12_セグメント発進力.md 用の画像生成スクリプト。

生成画像:
  01_segment_coverage.png       — セグメントデータカバレッジ（13 yuho vs 233 statements）
  02_sony_segment_portfolio.png — ソニーG 6 セグメントの売上 × 営利構造
  03_segment_yoy_acceleration.png — セグメント前期比成長率 加速 Top10 / 減速 Worst10
  04_high_margin_segments.png   — 営業利益率 30%超 セグメント発掘
  05_major_companies_2yr.png    — トヨタ / ソニーG / 信越化 / 任天堂 の 2 年セグメント推移

実行: python scripts/blog/11_segment_analysis_make_images.py
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
from matplotlib.patches import Rectangle

from utils.master_names import load_price_targets_names


# ── デザイン設定 ────────────────────────────────────────────────────────────
bs.apply_rcparams()
FIG_W = bs.FIG_W

C_UP    = "#5a9a72"
C_DOWN  = "#c87878"
C_OI    = "#f39c12"
C_NS    = "#3498db"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"


def _short(s: str, n: int) -> str:
    """長いラベルを n 文字に切り詰め、省略時は … を付ける（縦軸ラベルの食い込み防止）。"""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/08_segment_analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)


_savefig_vpad = bs.savefig_uniform   # 横幅も統一して保存（共通モジュール）


STMTS = Path(r"C:/stock_analysis/data/statements")
YUHO  = Path(r"C:/stock_analysis/data/yuho")


def get_segment_value(s: dict, keys: list[str]) -> float | None:
    """セグメント dict から複数候補キーで値を取り出す。"""
    for k in keys:
        v = s.get(k)
        if isinstance(v, (int, float)):
            return v
    return None


def load_segment_timeseries() -> tuple[dict[str, dict[str, list]], dict[str, str]]:
    """各銘柄について {fy_end: [segments]} の辞書を返す。"""
    by_code: dict[str, dict[str, list]] = {}
    names: dict[str, str] = {}

    for f in STMTS.glob("*_FY.json"):
        if "forecast" in f.name:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {})
        code = meta.get("code")
        if not code:
            continue
        seg = d.get("segments", {})
        cur = seg.get("current", []) if isinstance(seg, dict) else []
        if not cur:
            continue
        fy = meta.get("fiscal_year_end")
        if not fy:
            continue
        if code not in by_code:
            by_code[code] = {}
        by_code[code][fy] = cur
        names[code] = (meta.get("company_name") or "")[:14]
    return by_code, names


def compute_yoy_growth(by_code: dict) -> pd.DataFrame:
    """全銘柄でセグメント前期比成長率を計算。"""
    rows = []
    for code, fy_map in by_code.items():
        yrs = sorted(fy_map.keys())
        if len(yrs) < 2:
            continue
        prev_yr, cur_yr = yrs[-2], yrs[-1]
        prev_map = {s.get("key"): s for s in fy_map[prev_yr]}
        for s in fy_map[cur_yr]:
            key = s.get("key")
            if key not in prev_map:
                continue
            cur_ns = get_segment_value(s, ["net_sales", "external_revenue", "total_revenue"])
            prv_ns = get_segment_value(prev_map[key],
                                       ["net_sales", "external_revenue", "total_revenue"])
            if cur_ns is None or prv_ns is None or abs(prv_ns) < 1e8:
                continue
            cur_oi = get_segment_value(s, ["operating_income", "segment_profit"])
            prv_oi = get_segment_value(prev_map[key], ["operating_income", "segment_profit"])
            sales_g = (cur_ns - prv_ns) / abs(prv_ns) * 100
            oi_g = None
            if cur_oi is not None and prv_oi is not None and abs(prv_oi) >= 1e7:
                oi_g = (cur_oi - prv_oi) / abs(prv_oi) * 100
            rows.append({
                "code": code,
                "segment": s.get("label") or key,
                "prev_yr": prev_yr[:4],
                "cur_yr": cur_yr[:4],
                "sales_growth": sales_g,
                "cur_sales_oku": cur_ns / 1e8,
                "prv_sales_oku": prv_ns / 1e8,
                "cur_oi_oku": cur_oi / 1e8 if cur_oi is not None else None,
                "oi_growth": oi_g,
            })
    return pd.DataFrame(rows)


# ── 1) セグメントカバレッジ ───────────────────────────────────────────────────
def make_segment_coverage(by_code: dict) -> None:
    fig, ax = plt.subplots(figsize=(FIG_W, 5.2))
    fig.subplots_adjust(top=0.86, bottom=0.04, left=0.015, right=0.985)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # 有報 (yuho)
    ax.add_patch(Rectangle((0.2, 2.45), 6.5, 1.25, facecolor="#FFE5E5",
                            edgecolor="#c87878", linewidth=1.5))
    ax.text(0.45, 3.42, "有報 XBRL（連載06-08 で構築）",
            fontsize=16, fontweight="bold", color="#c87878", va="center")
    ax.text(0.45, 2.98, "13 銘柄 × 7 期 = 91 ファイル / セグメント取得 0 件",
            fontsize=14, color=C_TEXT, va="center")
    ax.text(0.45, 2.66, "★ parser_version 0.2.0 で yuho セグメント未対応",
            fontsize=14, color=C_TEXT_SUB, va="center", style="italic")

    # 決算短信 (statements)
    ax.add_patch(Rectangle((7.3, 2.45), 6.5, 1.25, facecolor="#E5FFE5",
                            edgecolor=C_UP, linewidth=1.5))
    ax.text(7.55, 3.42, "決算短信 XBRL（連載07 で構築）",
            fontsize=16, fontweight="bold", color=C_UP, va="center")
    ax.text(7.55, 2.98, "1,368 ファイル / セグメント取得 616 ファイル",
            fontsize=14, color=C_TEXT, va="center")
    n_2yrs = sum(1 for fy_map in by_code.values() if len(fy_map) >= 2)
    ax.text(7.55, 2.66, f"★ 2 年分時系列を持つ銘柄: {n_2yrs} 銘柄",
            fontsize=14, color=C_UP, va="center", fontweight="bold")

    # サンプル銘柄
    ax.add_patch(Rectangle((0.2, 0.45), 13.6, 1.5, facecolor="#F5F5F5",
                            edgecolor="#888888", linewidth=1.0))
    ax.text(0.45, 1.75, "本記事で扱う代表銘柄（連載01-11 と接続）",
            fontsize=16, fontweight="bold", color=C_TEXT, va="center")
    samples = [
        ("ソニーＧ", "6758", "6 セグメント / 連載02 主要 6 社"),
        ("トヨタ", "7203", "3 セグメント / 連載01-11 全登場"),
        ("信越化", "4063", "4 セグメント / 連載01 主要 15 社"),
        ("任天堂", "7974", "6 セグメント / 連載02・11 で登場"),
    ]
    x = 0.5
    for label, code, note in samples:
        ax.text(x, 1.18, f"{label} ({code})",
                fontsize=15, fontweight="bold", color=C_TEXT, va="center")
        ax.text(x, 0.78, note, fontsize=12.5, color=C_TEXT_SUB, va="center")
        x += 3.4

    ax.set_title(
        "セグメント情報のデータカバレッジ  ―  決算短信 XBRL からの 2 年時系列で実施",
        fontsize=21, fontweight="bold", color=C_TEXT, pad=34, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "01_segment_coverage.png")
    plt.close(fig)


# ── 2) ソニーG 6 セグメントの売上 × 営利構造 ──────────────────────────────────
def make_sony_portfolio(by_code: dict) -> None:
    code = "6758"
    if code not in by_code or len(by_code[code]) < 1:
        return
    yrs = sorted(by_code[code].keys())
    latest = by_code[code][yrs[-1]]

    seg_data = []
    for s in latest:
        ns = get_segment_value(s, ["net_sales", "external_revenue", "total_revenue"])
        oi = get_segment_value(s, ["operating_income", "segment_profit"])
        if ns is None:
            continue
        seg_data.append({
            "label": s.get("label") or s.get("key"),
            "sales_oku": ns / 1e8,
            "oi_oku": oi / 1e8 if isinstance(oi, (int, float)) else 0,
            "margin": (oi / ns * 100) if isinstance(oi, (int, float)) and ns != 0 else None,
        })
    df = pd.DataFrame(seg_data).sort_values("sales_oku", ascending=True)

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(FIG_W, 6.6),
                                     gridspec_kw=dict(width_ratios=[1.25, 1],
                                                      wspace=0.45))
    fig.subplots_adjust(top=0.75, bottom=0.12, left=0.165, right=0.985)

    # 左: 売上構成
    y = np.arange(len(df))
    bw = 0.38
    smax = df["sales_oku"].max()
    ax_l.barh(y - bw / 2, df["sales_oku"], height=bw, color=C_NS,
              alpha=0.9, edgecolor="white", linewidth=0.8, label="売上（億円）")
    ax_l.barh(y + bw / 2, df["oi_oku"], height=bw, color=C_OI,
              alpha=0.9, edgecolor="white", linewidth=0.8, label="営業利益（億円）")
    for i, r in df.reset_index(drop=True).iterrows():
        ax_l.text(r["sales_oku"] + smax * 0.012, i - bw / 2, f"{r['sales_oku']:,.0f}億",
                  va="center", fontsize=15, color=C_NS, fontweight="bold")
        ax_l.text(max(r["oi_oku"], 0) + smax * 0.012, i + bw / 2, f"{r['oi_oku']:,.0f}億",
                  va="center", fontsize=15, color=C_OI, fontweight="bold")
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([_short(s, 13) for s in df["label"]], fontsize=15)
    ax_l.set_xlim(0, smax * 1.22)
    ax_l.set_xlabel("億円", fontsize=17, color=C_TEXT_SUB)
    ax_l.tick_params(axis="x", labelsize=15)
    ax_l.legend(loc="lower right", fontsize=15, frameon=True,
                facecolor="white", edgecolor="#dddddd")
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title(f"6 セグメントの売上 × 営業利益（{yrs[-1][:4]} 年度）",
                   fontsize=18, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    # 右: 営業利益率（赤字セグメントは率の比較になじまないので除外）
    df_m = df.dropna(subset=["margin"])
    df_m = df_m[df_m["margin"].between(0, 100)].sort_values("margin", ascending=True)
    y2 = np.arange(len(df_m))
    mmax = df_m["margin"].max()
    colors = [C_UP if m >= 15 else "#85c1e9" if m >= 8 else "#888888" for m in df_m["margin"]]
    ax_r.barh(y2, df_m["margin"], color=colors, alpha=0.9,
              edgecolor="white", linewidth=0.8)
    for i, r in df_m.reset_index(drop=True).iterrows():
        ax_r.text(r["margin"] + mmax * 0.02, i, f"{r['margin']:.1f}%",
                  va="center", fontsize=15, fontweight="bold", color=C_TEXT)
    ax_r.set_yticks(y2)
    ax_r.set_yticklabels([_short(s, 13) for s in df_m["label"]], fontsize=15)
    ax_r.set_xlabel("営業利益率（%）", fontsize=17, color=C_TEXT)
    ax_r.set_xlim(0, mmax * 1.28)
    ax_r.tick_params(axis="x", labelsize=15)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("セグメント別 営業利益率  ―  音楽が突出",
                   fontsize=18, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    fig.suptitle("ソニーグループの事業ポートフォリオ  ―  6 セグメントの収益構造",
                 fontsize=23, fontweight="bold", color=C_TEXT, y=0.965)
    _savefig_vpad(fig, OUT_DIR / "02_sony_segment_portfolio.png")
    plt.close(fig)


# ── 3) セグメント前期比成長率 加速 Top10 / 減速 Worst10 ─────────────────────
def make_yoy_acceleration(dfg: pd.DataFrame, names: dict[str, str]) -> None:
    # 規模 100 億以上で絞る
    sub = dfg[dfg["cur_sales_oku"] >= 100].copy()
    # 異常値除外（前期がゼロ近傍で発散したもの）
    sub = sub[sub["sales_growth"].between(-90, 500)]
    sub["name"] = sub["code"].map(names).fillna("")

    top = sub.nlargest(10, "sales_growth").iloc[::-1]
    worst = sub.nsmallest(10, "sales_growth").iloc[::-1]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(FIG_W, 8.4),
                                     gridspec_kw=dict(wspace=0.62))
    fig.subplots_adjust(top=0.80, bottom=0.09, left=0.17, right=0.985)

    def _ylab(r):
        return f"{r['code']} {_short(r['name'], 9)}\n{_short(r['segment'], 15)}"

    # 加速 Top10
    y = np.arange(len(top))
    gmax = top["sales_growth"].max()
    ax_l.barh(y, top["sales_growth"], color=C_UP, alpha=0.9,
              edgecolor="white", linewidth=0.8)
    for i, r in top.reset_index(drop=True).iterrows():
        ax_l.text(r["sales_growth"] + gmax * 0.02, i,
                  f"+{r['sales_growth']:.1f}%（売上 {r['cur_sales_oku']:,.0f}億）",
                  va="center", fontsize=14, color=C_UP, fontweight="bold")
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([_ylab(r) for _, r in top.iterrows()], fontsize=14)
    ax_l.set_xlabel("売上前期比成長率（%）", fontsize=17, color=C_TEXT_SUB)
    ax_l.set_xlim(0, gmax * 1.55)
    ax_l.tick_params(axis="x", labelsize=15)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("★ 加速 Top10  ―  売上 100 億以上のセグメント",
                   fontsize=18, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    # 減速 Worst10
    y = np.arange(len(worst))
    gmin = worst["sales_growth"].min()
    ax_r.barh(y, worst["sales_growth"], color=C_DOWN, alpha=0.9,
              edgecolor="white", linewidth=0.8)
    for i, r in worst.reset_index(drop=True).iterrows():
        ax_r.text(r["sales_growth"] - abs(gmin) * 0.02, i,
                  f"{r['sales_growth']:.1f}%（{r['cur_sales_oku']:,.0f}億）",
                  va="center", ha="right", fontsize=14, color=C_DOWN, fontweight="bold")
    ax_r.set_yticks(y)
    ax_r.set_yticklabels([_ylab(r) for _, r in worst.iterrows()], fontsize=14)
    ax_r.set_xlabel("売上前期比成長率（%）", fontsize=17, color=C_TEXT_SUB)
    ax_r.set_xlim(gmin * 1.55, 0)
    ax_r.tick_params(axis="x", labelsize=15)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("⚠ 減速 Worst10  ―  売上 100 億以上のセグメント",
                   fontsize=18, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    fig.suptitle(
        f"セグメント別 前期比成長率  ―  決算短信 2 年分から抽出（対象 {len(sub)} セグメント）",
        fontsize=23, fontweight="bold", color=C_TEXT, y=0.965)
    _savefig_vpad(fig, OUT_DIR / "03_segment_yoy_acceleration.png")
    plt.close(fig)


# ── 4) 高利益率セグメント発掘 ────────────────────────────────────────────────
def make_high_margin_segments(dfg: pd.DataFrame, names: dict[str, str]) -> None:
    sub = dfg.copy()
    sub = sub[sub["cur_sales_oku"] >= 200]
    sub = sub.dropna(subset=["cur_oi_oku"])
    sub["margin"] = sub["cur_oi_oku"] / sub["cur_sales_oku"] * 100
    sub["name"] = sub["code"].map(names).fillna("")
    sub = sub[sub["margin"].between(0, 100)]
    top = sub.nlargest(15, "margin").iloc[::-1]

    fig, ax = plt.subplots(figsize=(FIG_W, 11))
    fig.subplots_adjust(top=0.88, bottom=0.07, left=0.2, right=0.985)
    y = np.arange(len(top))
    mmax = top["margin"].max()
    colors = [C_UP if m >= 30 else C_OI if m >= 20 else "#85c1e9" for m in top["margin"]]
    ax.barh(y, top["margin"], color=colors, alpha=0.9,
            edgecolor="white", linewidth=0.8, height=0.62)
    for i, r in top.reset_index(drop=True).iterrows():
        ax.text(r["margin"] + mmax * 0.012, i,
                f"{r['margin']:.1f}%（売上 {r['cur_sales_oku']:,.0f}億 / 営利 {r['cur_oi_oku']:,.0f}億）",
                va="center", fontsize=14, color=C_TEXT, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {_short(r['name'], 10)}\n{_short(r['segment'], 16)}"
                        for _, r in top.iterrows()], fontsize=15)
    ax.set_xlabel("営業利益率（%）", fontsize=17, color=C_TEXT)
    ax.set_xlim(0, mmax * 1.5)
    ax.tick_params(axis="x", labelsize=15)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "高営業利益率セグメント Top15  ―  売上 200 億以上 × 利益率 > 0%",
        fontsize=22, fontweight="bold", color=C_TEXT, pad=32, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "04_high_margin_segments.png")
    plt.close(fig)


# ── 5) 主要 4 銘柄の 2 年セグメント推移 ────────────────────────────────────
def make_major_companies_2yr(by_code: dict, names: dict[str, str]) -> None:
    targets = [("7203", "トヨタ"), ("6758", "ソニーＧ"),
               ("4063", "信越化"), ("7974", "任天堂")]

    # セグメント別「売上」を 2 年分プロットできる銘柄だけを先に確定させる
    # （例: トヨタはセグメントに営業利益しか無く売上が取れないため除外される）
    plots = []
    for code, name in targets:
        if code not in by_code or len(by_code[code]) < 2:
            continue
        yrs = sorted(by_code[code].keys())
        prev_yr, cur_yr = yrs[-2], yrs[-1]
        prev_map = {s.get("key"): s for s in by_code[code][prev_yr]}
        rows = []
        for s in by_code[code][cur_yr]:
            key = s.get("key")
            label = s.get("label") or key
            cur_ns = get_segment_value(s, ["net_sales", "external_revenue", "total_revenue"])
            prv_ns = get_segment_value(prev_map.get(key, {}),
                                       ["net_sales", "external_revenue", "total_revenue"])
            if cur_ns is None:
                continue
            rows.append({"label": label[:14],
                         "prv": prv_ns / 1e8 if prv_ns else 0,
                         "cur": cur_ns / 1e8,
                         "growth": ((cur_ns - prv_ns) / abs(prv_ns) * 100) if prv_ns else None})
        if not rows:
            continue
        df = pd.DataFrame(rows).sort_values("cur", ascending=True)
        plots.append((code, name, prev_yr, cur_yr, df))

    if not plots:
        return

    # 描画可能銘柄数に応じてレイアウトを決定。セグメント名が長いので
    # 2 社までは縦積み（各パネル全幅）にしてラベル衝突を避ける。
    n = len(plots)
    keys = [chr(ord("a") + i) for i in range(n)]
    if n == 1:
        mosaic, figsize, top = [["a"]], (FIG_W, 4.8), 0.79
    elif n == 2:
        mosaic, figsize, top = [["a"], ["b"]], (FIG_W, 9.2), 0.79
    elif n == 3:
        mosaic, figsize, top = [["a", "b"], ["c", "c"]], (FIG_W, 10), 0.83
    else:
        mosaic, figsize, top = [["a", "b"], ["c", "d"]], (FIG_W, 10), 0.83

    fig, axd = plt.subplot_mosaic(mosaic, figsize=figsize)
    fig.subplots_adjust(top=top, bottom=0.08, left=0.2, right=0.98,
                        hspace=0.55, wspace=0.5)
    axes = [axd[k] for k in keys]

    for ax, (code, name, prev_yr, cur_yr, df) in zip(axes, plots):
        y = np.arange(len(df))
        bw = 0.36
        ax.barh(y - bw / 2, df["prv"], height=bw, color="#aaaaaa",
                alpha=0.7, edgecolor="white", linewidth=0.5,
                label=f"{prev_yr[:4]}")
        ax.barh(y + bw / 2, df["cur"], height=bw, color=C_NS,
                alpha=0.85, edgecolor="white", linewidth=0.8,
                label=f"{cur_yr[:4]}")
        cmax = max(df["cur"].max(), df["prv"].max())
        for i, r in df.reset_index(drop=True).iterrows():
            g = r["growth"]
            if g is not None:
                col = C_UP if g >= 0 else C_DOWN
                ax.text(max(r["cur"], r["prv"]) + cmax * 0.02, i,
                        f"{g:+.1f}%", va="center", fontsize=15,
                        color=col, fontweight="bold")
        ax.set_xlim(0, cmax * 1.2)
        ax.set_yticks(y)
        ax.set_yticklabels([_short(s, 14) for s in df["label"]], fontsize=15)
        ax.set_xlabel("売上（億円）", fontsize=16, color=C_TEXT_SUB)
        ax.tick_params(axis="x", labelsize=14)
        ax.legend(loc="lower right", fontsize=15, frameon=True,
                  facecolor="white", edgecolor="#dddddd")
        ax.grid(axis="x", color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_title(f"{name} ({code})", fontsize=18,
                     fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle(
        f"主要 {len(plots)} 銘柄のセグメント 2 年推移  ―  決算短信 XBRL から抽出",
        fontsize=23, fontweight="bold", color=C_TEXT, y=0.975)
    _savefig_vpad(fig, OUT_DIR / "05_major_companies_2yr.png")
    plt.close(fig)


# ── 6) ENEOS のピークアウト内訳 ────────────────────────────────────────────
def make_eneos_peakout(by_code: dict) -> None:
    """ENEOS 5 セグメントの売上・営業利益・OPM を当期 vs 前期で比較。

    narrative: 連結営業利益は赤字脱却で +542% 急回復したが、開発・機能材の
    OPM は急低下。表面の「回復」の下にあるピークアウト構図を可視化する。

    ENEOS は決算短信 JSON が直近 1 期分しか無いが、その JSON 内の
    segments.prior に前期データが含まれているのでそれを利用する。
    """
    code = "5020"
    # 直接 JSON から current / prior を取得（by_code は 1 期分しか無いため）
    cands = list(STMTS.glob(f"{code}_*_FY.json"))
    if not cands:
        return
    latest = max(cands, key=lambda p: p.stem)
    try:
        d = json.load(open(latest, encoding="utf-8"))
    except Exception:
        return
    seg = d.get("segments") or {}
    current = seg.get("current") or []
    prior   = seg.get("prior") or []
    if not current or not prior:
        return

    fy = (d.get("metadata") or {}).get("fiscal_year_end", "")
    cur_yr = fy[:4] if fy else ""
    prev_yr = str(int(cur_yr) - 1) if cur_yr.isdigit() else ""

    prev_map = {s.get("key"): s for s in prior}

    rows = []
    for s in current:
        key = s.get("key")
        label = s.get("label") or key
        cur_rev = get_segment_value(s, ["total_revenue", "net_sales", "external_revenue"])
        cur_op  = s.get("operating_income")
        prv_rev = get_segment_value(prev_map.get(key, {}),
                                    ["total_revenue", "net_sales", "external_revenue"])
        prv_op  = prev_map.get(key, {}).get("operating_income")
        if cur_rev is None or cur_op is None:
            continue
        rows.append({
            "label": label, "cur_rev": cur_rev / 1e8, "cur_op": cur_op / 1e8,
            "prv_rev": (prv_rev or 0) / 1e8, "prv_op": (prv_op or 0) / 1e8,
            "cur_opm": cur_op / cur_rev * 100 if cur_rev else 0,
            "prv_opm": (prv_op / prv_rev * 100) if prv_rev else 0,
        })
    if not rows:
        return
    # 売上の大きい順
    df = pd.DataFrame(rows).sort_values("cur_rev", ascending=True).reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 6.4),
                             gridspec_kw=dict(wspace=0.5))
    fig.subplots_adjust(top=0.75, bottom=0.13, left=0.135, right=0.985)

    ylab = [_short(s, 11) for s in df["label"]]

    # 左: 営業利益（億円）
    ax = axes[0]
    y = np.arange(len(df))
    bw = 0.38
    op_min = min(df["prv_op"].min(), df["cur_op"].min(), 0.0)
    op_max = max(df["prv_op"].max(), df["cur_op"].max(), 0.0)
    op_span = (op_max - op_min) or 1.0
    ax.barh(y - bw / 2, df["prv_op"], height=bw, color="#aaaaaa",
            alpha=0.75, edgecolor="white", linewidth=0.5, label=f"{prev_yr[:4]}")
    ax.barh(y + bw / 2, df["cur_op"], height=bw, color=C_NS,
            alpha=0.9, edgecolor="white", linewidth=0.8, label=f"{cur_yr[:4]}")
    for i, r in df.iterrows():
        diff = r["cur_op"] - r["prv_op"]
        col = C_UP if diff >= 0 else C_DOWN
        ax.text(max(r["cur_op"], r["prv_op"]) + op_span * 0.02, i, f"{diff:+,.0f}億",
                va="center", fontsize=15, color=col, fontweight="bold")
    ax.axvline(0, color="#888888", linewidth=0.6)
    ax.set_xlim(op_min - op_span * 0.08, op_max + op_span * 0.24)
    ax.set_yticks(y)
    ax.set_yticklabels(ylab, fontsize=15)
    ax.set_xlabel("営業利益（億円）", fontsize=17, color=C_TEXT_SUB)
    ax.tick_params(axis="x", labelsize=15)
    ax.legend(loc="lower right", fontsize=15, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("セグメント別 営業利益", fontsize=18,
                 fontweight="bold", color=C_TEXT, pad=30, loc="left")

    # 右: 営業利益率（%）
    ax = axes[1]
    m_min = min(df["prv_opm"].min(), df["cur_opm"].min(), 0.0)
    m_max = max(df["prv_opm"].max(), df["cur_opm"].max(), 0.0)
    m_span = (m_max - m_min) or 1.0
    ax.barh(y - bw / 2, df["prv_opm"], height=bw, color="#aaaaaa",
            alpha=0.75, edgecolor="white", linewidth=0.5, label=f"{prev_yr[:4]}")
    ax.barh(y + bw / 2, df["cur_opm"], height=bw, color="#E08C5C",
            alpha=0.9, edgecolor="white", linewidth=0.8, label=f"{cur_yr[:4]}")
    for i, r in df.iterrows():
        diff = r["cur_opm"] - r["prv_opm"]
        col = C_UP if diff >= 0 else C_DOWN
        ax.text(max(r["cur_opm"], r["prv_opm"]) + m_span * 0.02, i, f"{diff:+.2f}pt",
                va="center", fontsize=15, color=col, fontweight="bold")
    ax.axvline(0, color="#888888", linewidth=0.6)
    ax.set_xlim(m_min - m_span * 0.06, m_max + m_span * 0.26)
    ax.set_yticks(y)
    ax.set_yticklabels(ylab, fontsize=15)
    ax.set_xlabel("営業利益率 OPM（%）", fontsize=17, color=C_TEXT_SUB)
    ax.tick_params(axis="x", labelsize=15)
    ax.legend(loc="lower right", fontsize=15, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("セグメント別 営業利益率（OPM）",
                 fontsize=18, fontweight="bold", color=C_TEXT, pad=30, loc="left")

    fig.suptitle(
        f"ＥＮＥＯＳ ({code}) のピークアウト内訳  ―  "
        f"{prev_yr[:4]}/3 期 vs {cur_yr[:4]}/3 期 セグメント比較",
        fontsize=23, fontweight="bold", color=C_TEXT, y=0.965)
    _savefig_vpad(fig, OUT_DIR / "06_eneos_segments.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    by_code, names_short = load_segment_timeseries()
    print(f"[load] セグメント保有銘柄: {len(by_code)} / 2 年以上: "
          f"{sum(1 for fy in by_code.values() if len(fy) >= 2)}")

    # 銘柄名は master_names を優先
    master_names = load_price_targets_names()
    for c in by_code:
        if c in master_names:
            names_short[c] = master_names[c][:14]

    dfg = compute_yoy_growth(by_code)
    print(f"[compute] YoY 成長率計算可能セグメント: {len(dfg)}")

    make_segment_coverage(by_code)
    print("[ok] 01_segment_coverage.png")
    make_sony_portfolio(by_code)
    print("[ok] 02_sony_segment_portfolio.png")
    make_yoy_acceleration(dfg, names_short)
    print("[ok] 03_segment_yoy_acceleration.png")
    make_high_margin_segments(dfg, names_short)
    print("[ok] 04_high_margin_segments.png")
    make_major_companies_2yr(by_code, names_short)
    print("[ok] 05_major_companies_2yr.png")
    make_eneos_peakout(by_code)
    print("[ok] 06_eneos_segments.png")
