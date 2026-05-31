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
from matplotlib.patches import Rectangle

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

C_UP    = "#5a9a72"
C_DOWN  = "#c87878"
C_OI    = "#f39c12"
C_NS    = "#3498db"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/11_segment_analysis")
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
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # 有報 (yuho)
    ax.add_patch(Rectangle((0.3, 2.5), 5.0, 1.2, facecolor="#FFE5E5",
                            edgecolor="#c87878", linewidth=1.5))
    ax.text(0.5, 3.4, "有報 XBRL（連載06-08 で構築）",
            fontsize=16, fontweight="bold", color="#c87878", va="center")
    ax.text(0.5, 2.95, "13 銘柄 × 7 期 = 91 ファイル / セグメント取得済み 0 件",
            fontsize=16, color=C_TEXT, va="center")
    ax.text(0.5, 2.65, "★ parser_version 0.2.0 で yuho セグメント未対応",
            fontsize=16, color=C_TEXT_SUB, va="center", style="italic")

    # 決算短信 (statements)
    ax.add_patch(Rectangle((6.0, 2.5), 5.2, 1.2, facecolor="#E5FFE5",
                            edgecolor=C_UP, linewidth=1.5))
    ax.text(6.2, 3.4, "決算短信 XBRL（連載07 で構築）",
            fontsize=16, fontweight="bold", color=C_UP, va="center")
    ax.text(6.2, 2.95, "1,368 ファイル / セグメント取得済み 616 ファイル",
            fontsize=16, color=C_TEXT, va="center")
    n_2yrs = sum(1 for fy_map in by_code.values() if len(fy_map) >= 2)
    ax.text(6.2, 2.65, f"★ 2 年分時系列を持つ銘柄: {n_2yrs} 銘柄",
            fontsize=16, color=C_UP, va="center", fontweight="bold")

    # サンプル銘柄
    ax.add_patch(Rectangle((0.3, 0.5), 10.9, 1.5, facecolor="#F5F5F5",
                            edgecolor="#888888", linewidth=1.0))
    ax.text(0.5, 1.8, "本記事で扱う代表銘柄（連載01-11 と接続）",
            fontsize=16, fontweight="bold", color=C_TEXT, va="center")
    samples = [
        ("ソニーＧ", "6758", "6 セグメント / 連載02 主要 6 社"),
        ("トヨタ", "7203", "3 セグメント / 連載01-11 全登場"),
        ("信越化", "4063", "4 セグメント / 連載01 主要 15 社"),
        ("任天堂", "7974", "6 セグメント / 連載02・11 で登場"),
    ]
    x = 0.6
    for label, code, note in samples:
        ax.text(x, 1.2, f"{label} ({code})",
                fontsize=16, fontweight="bold", color=C_TEXT)
        ax.text(x, 0.85, note, fontsize=16, color=C_TEXT_SUB)
        x += 2.7

    ax.set_title(
        "セグメント情報のデータカバレッジ  ―  決算短信 XBRL からの 2 年時系列で実施",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
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

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 6.5),
                                     gridspec_kw=dict(wspace=0.35))
    fig.subplots_adjust(top=0.82)

    # 左: 売上構成
    y = np.arange(len(df))
    bw = 0.36
    ax_l.barh(y - bw / 2, df["sales_oku"], height=bw, color=C_NS,
              alpha=0.85, edgecolor="white", linewidth=0.8, label="売上（億円）")
    ax_l.barh(y + bw / 2, df["oi_oku"], height=bw, color=C_OI,
              alpha=0.85, edgecolor="white", linewidth=0.8, label="営業利益（億円）")
    for i, r in df.reset_index(drop=True).iterrows():
        ax_l.text(r["sales_oku"] + 200, i - bw / 2, f"{r['sales_oku']:,.0f}億",
                  va="center", fontsize=16, color=C_NS, fontweight="bold")
        ax_l.text(r["oi_oku"] + 200, i + bw / 2, f"{r['oi_oku']:,.0f}億",
                  va="center", fontsize=16, color=C_OI, fontweight="bold")
    ax_l.set_yticks(y)
    ax_l.set_yticklabels(df["label"].str[:24], fontsize=16)
    ax_l.set_xlabel("億円", fontsize=16, color=C_TEXT_SUB)
    ax_l.legend(loc="lower right", fontsize=16, frameon=False)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title(f"ソニーＧ  ―  6 セグメントの売上 × 営業利益（{yrs[-1][:4]} 年度）",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 右: 営業利益率
    df_m = df.dropna(subset=["margin"]).sort_values("margin", ascending=True)
    y2 = np.arange(len(df_m))
    colors = [C_UP if m >= 15 else "#85c1e9" if m >= 8 else "#888888" for m in df_m["margin"]]
    ax_r.barh(y2, df_m["margin"], color=colors, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, r in df_m.reset_index(drop=True).iterrows():
        ax_r.text(r["margin"] + 0.4, i, f"{r['margin']:.1f}%",
                  va="center", fontsize=16, fontweight="bold", color=C_TEXT)
    ax_r.set_yticks(y2)
    ax_r.set_yticklabels(df_m["label"].str[:24], fontsize=16)
    ax_r.set_xlabel("営業利益率（%）", fontsize=16, color=C_TEXT)
    ax_r.set_xlim(0, max(df_m["margin"]) * 1.2)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("セグメント別 営業利益率  ―  音楽セグメントが突出",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle("ソニーグループの事業ポートフォリオ  ―  6 セグメントの収益構造",
                 fontsize=20, fontweight="bold", color=C_TEXT, y=0.97)
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

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14.5, 7),
                                     gridspec_kw=dict(wspace=0.55))

    # 加速 Top10
    y = np.arange(len(top))
    ax_l.barh(y, top["sales_growth"], color=C_UP, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, r in top.reset_index(drop=True).iterrows():
        ax_l.text(r["sales_growth"] + 3, i,
                  f"+{r['sales_growth']:.1f}%  (売上 {r['cur_sales_oku']:,.0f}億)",
                  va="center", fontsize=16, color=C_UP, fontweight="bold")
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([f"{r['code']} {r['name'][:9]}\n  {r['segment'][:16]}"
                          for _, r in top.iterrows()], fontsize=16)
    ax_l.set_xlabel("売上前期比成長率（%）", fontsize=16, color=C_TEXT_SUB)
    ax_l.set_xlim(0, max(top["sales_growth"]) * 1.5)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("★ 加速 Top10  ―  売上 100 億以上のセグメント",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 減速 Worst10
    y = np.arange(len(worst))
    ax_r.barh(y, worst["sales_growth"], color=C_DOWN, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, r in worst.reset_index(drop=True).iterrows():
        ax_r.text(r["sales_growth"] - 0.5, i,
                  f"{r['sales_growth']:.1f}%  (売上 {r['cur_sales_oku']:,.0f}億)",
                  va="center", ha="right", fontsize=16, color=C_DOWN, fontweight="bold")
    ax_r.set_yticks(y)
    ax_r.set_yticklabels([f"{r['code']} {r['name'][:9]}\n  {r['segment'][:16]}"
                          for _, r in worst.iterrows()], fontsize=16)
    ax_r.set_xlabel("売上前期比成長率（%）", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_xlim(min(worst["sales_growth"]) * 1.25, 0)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("⚠ 減速 Worst10  ―  売上 100 億以上のセグメント",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle(
        f"セグメント別 前期比成長率  ―  決算短信 2 年分から抽出（対象 {len(sub)} セグメント）",
        fontsize=20, fontweight="bold", color=C_TEXT, y=1.02)
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

    fig, ax = plt.subplots(figsize=(13.5, 8))
    y = np.arange(len(top))
    colors = [C_UP if m >= 30 else C_OI if m >= 20 else "#85c1e9" for m in top["margin"]]
    ax.barh(y, top["margin"], color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.8)
    for i, r in top.reset_index(drop=True).iterrows():
        ax.text(r["margin"] + 0.5, i,
                f"{r['margin']:.1f}%  (売上 {r['cur_sales_oku']:,.0f}億 / 営利 {r['cur_oi_oku']:,.0f}億)",
                va="center", fontsize=16, color=C_TEXT, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['code']} {r['name'][:10]}\n  {r['segment'][:18]}"
                        for _, r in top.iterrows()], fontsize=16)
    ax.set_xlabel("営業利益率（%）", fontsize=16, color=C_TEXT)
    ax.set_xlim(0, max(top["margin"]) * 1.4)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "高営業利益率セグメント Top15  ―  売上 200 億以上 × 利益率 > 0%",
        fontsize=20, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "04_high_margin_segments.png")
    plt.close(fig)


# ── 5) 主要 4 銘柄の 2 年セグメント推移 ────────────────────────────────────
def make_major_companies_2yr(by_code: dict, names: dict[str, str]) -> None:
    targets = [("7203", "トヨタ"), ("6758", "ソニーＧ"),
               ("4063", "信越化"), ("7974", "任天堂")]

    # 利用可能銘柄のみ
    avail = [(c, n) for c, n in targets if c in by_code and len(by_code[c]) >= 2]
    if not avail:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10),
                             gridspec_kw=dict(hspace=0.45, wspace=0.35))
    axes = axes.flatten()

    for ax, (code, name) in zip(axes, avail):
        yrs = sorted(by_code[code].keys())
        if len(yrs) < 2:
            ax.axis("off")
            continue
        prev_yr, cur_yr = yrs[-2], yrs[-1]

        # セグメント別売上を 2 年並べる
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
            ax.axis("off")
            continue
        df = pd.DataFrame(rows).sort_values("cur", ascending=True)

        y = np.arange(len(df))
        bw = 0.36
        ax.barh(y - bw / 2, df["prv"], height=bw, color="#aaaaaa",
                alpha=0.7, edgecolor="white", linewidth=0.5,
                label=f"{prev_yr[:4]}")
        ax.barh(y + bw / 2, df["cur"], height=bw, color=C_NS,
                alpha=0.85, edgecolor="white", linewidth=0.8,
                label=f"{cur_yr[:4]}")
        for i, r in df.reset_index(drop=True).iterrows():
            g = r["growth"]
            if g is not None:
                col = C_UP if g >= 0 else C_DOWN
                ax.text(r["cur"] + max(df["cur"]) * 0.02, i + bw / 2,
                        f"{g:+.1f}%", va="center", fontsize=16,
                        color=col, fontweight="bold")
        ax.set_yticks(y)
        ax.set_yticklabels(df["label"], fontsize=16)
        ax.set_xlabel("売上（億円）", fontsize=16, color=C_TEXT_SUB)
        ax.legend(loc="lower right", fontsize=16, frameon=False)
        ax.grid(axis="x", color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_title(f"{name} ({code})", fontsize=16,
                     fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 余ったセルを消す
    for ax in axes[len(avail):]:
        ax.axis("off")

    fig.suptitle(
        "主要 4 銘柄のセグメント 2 年推移  ―  決算短信 XBRL から抽出",
        fontsize=20, fontweight="bold", color=C_TEXT, y=1.00)
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

    fig, axes = plt.subplots(1, 2, figsize=(14, 6),
                             gridspec_kw=dict(wspace=0.35))
    fig.subplots_adjust(top=0.82)

    # 左: 営業利益（億円）
    ax = axes[0]
    y = np.arange(len(df))
    bw = 0.36
    ax.barh(y - bw / 2, df["prv_op"], height=bw, color="#aaaaaa",
            alpha=0.7, edgecolor="white", linewidth=0.5, label=f"{prev_yr[:4]}")
    ax.barh(y + bw / 2, df["cur_op"], height=bw, color=C_NS,
            alpha=0.85, edgecolor="white", linewidth=0.8, label=f"{cur_yr[:4]}")
    for i, r in df.iterrows():
        diff = r["cur_op"] - r["prv_op"]
        col = C_UP if diff >= 0 else C_DOWN
        x_text = max(r["cur_op"], r["prv_op"]) + max(df["cur_op"].abs().max(),
                                                      df["prv_op"].abs().max()) * 0.03
        ax.text(x_text, i, f"{diff:+,.0f}億",
                va="center", fontsize=16, color=col, fontweight="bold")
    ax.axvline(0, color="#888888", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(df["label"], fontsize=16)
    ax.set_xlabel("営業利益（億円）", fontsize=16, color=C_TEXT_SUB)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("セグメント別 営業利益", fontsize=16,
                 fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 右: 営業利益率（%）
    ax = axes[1]
    ax.barh(y - bw / 2, df["prv_opm"], height=bw, color="#aaaaaa",
            alpha=0.7, edgecolor="white", linewidth=0.5, label=f"{prev_yr[:4]}")
    ax.barh(y + bw / 2, df["cur_opm"], height=bw, color="#E08C5C",
            alpha=0.85, edgecolor="white", linewidth=0.8, label=f"{cur_yr[:4]}")
    for i, r in df.iterrows():
        diff = r["cur_opm"] - r["prv_opm"]
        col = C_UP if diff >= 0 else C_DOWN
        x_text = max(r["cur_opm"], r["prv_opm"]) + 1.5
        if r["cur_opm"] < 0 and r["prv_opm"] < 0:
            x_text = max(r["cur_opm"], r["prv_opm"]) + 1.5
        ax.text(x_text, i, f"{diff:+.2f}pt",
                va="center", fontsize=16, color=col, fontweight="bold")
    ax.axvline(0, color="#888888", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(df["label"], fontsize=16)
    ax.set_xlabel("営業利益率 OPM（%）", fontsize=16, color=C_TEXT_SUB)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("セグメント別 営業利益率（OPM）",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    fig.suptitle(
        f"ＥＮＥＯＳ ({code}) のピークアウト内訳  ―  "
        f"{prev_yr[:4]}/3 期 vs {cur_yr[:4]}/3 期 セグメント比較",
        fontsize=20, fontweight="bold", color=C_TEXT, y=0.97)
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
