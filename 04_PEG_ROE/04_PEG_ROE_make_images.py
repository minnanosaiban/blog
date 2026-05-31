"""
blog/01_PEG_ROE銘柄分析.md 用の画像生成スクリプト。

生成画像:
  01_garp_map.png        — GARPマップ全体（散布図 + 主要銘柄ハイライト）
  02_majors_table.png    — 主要銘柄 GARP スコアテーブル
  03_oil_refining.png    — 石油元売3社の GARP 位置 + 指標カード
  04_majors_charts.png   — 主要銘柄の直近6ヶ月株価チャート（小型グリッド）
  05_oil_charts.png      — 石油元売3社の直近6ヶ月株価チャート

実行: python scripts/blog/04_garp_peg_roe_make_images.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, r"C:\stock_analysis")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

from config.paths import rakunav_file, PRICES_STOCKS_DAILY
from utils.price_refresh import refresh_with_yfinance
from utils.master_names import apply_master_names, load_price_targets_names
from utils.universe_topix500 import filter_to_topix500, topix_large100_codes


# ── デザイン設定 ────────────────────────────────────────────────────────────
mpl.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP"]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["figure.facecolor"] = "white"
mpl.rcParams["axes.facecolor"] = "white"
mpl.rcParams["savefig.facecolor"] = "white"
mpl.rcParams["savefig.bbox"] = "tight"
mpl.rcParams["savefig.dpi"] = 144
mpl.rcParams["savefig.pad_inches"] = 0  # 左右余白なし（上下は _savefig_vpad で制御）
mpl.rcParams["axes.titlepad"] = 30
# フォントサイズ（800px カラムで 1872px 画像 → 約 43% に圧縮されるため底上げ）
mpl.rcParams["font.size"] = 16
mpl.rcParams["axes.titlesize"] = 20
mpl.rcParams["axes.labelsize"] = 16
mpl.rcParams["xtick.labelsize"] = 16
mpl.rcParams["ytick.labelsize"] = 16
mpl.rcParams["legend.fontsize"] = 16

# カラーパレット
C_GARP_IDEAL = "#5a9a72"  # 緑: GARP理想ゾーン
C_GROWTH     = "#f39c12"  # オレンジ: 割高グロース
C_VALUE      = "#3498db"  # 青: バリュー候補
C_INVALID    = "#c87878"  # 赤: 投資不適格
C_NEUTRAL    = "#cccccc"  # グレー: その他
C_TEXT       = "#202124"
C_TEXT_SUB   = "#70757a"
C_GRID       = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/04_garp_peg_roe")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _savefig_vpad(fig: plt.Figure, path: Path,
                  tpad: float = 0.4, bpad: float = 0.5) -> None:
    """上 tpad / 下 bpad インチの余白を追加して保存する（左右は余白なし）。"""
    import io
    import numpy as np
    buf = io.BytesIO()
    fig.savefig(buf, bbox_inches="tight", pad_inches=0, format="png")
    buf.seek(0)
    img = plt.imread(buf)                            # RGBA float32 (H, W, 4)
    top_rows = max(1, round(tpad * fig.dpi))
    bot_rows = max(1, round(bpad * fig.dpi))
    white_top = np.ones((top_rows, img.shape[1], img.shape[2]), dtype=img.dtype)
    white_bot = np.ones((bot_rows, img.shape[1], img.shape[2]), dtype=img.dtype)
    plt.imsave(str(path), np.vstack([white_top, img, white_bot]), dpi=fig.dpi)


# ── データ準備 ─────────────────────────────────────────────────────────────
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


def load_universe() -> pd.DataFrame:
    frames = []
    for no in (118, 113, 213):
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str)
        df["コード"] = df["コード"].astype(str).str.strip()
        for col in df.columns:
            if col not in ("コード", "銘柄名", "市場", "財務"):
                df[col] = df[col].map(_to_float)
        frames.append(df)
    merged = frames[0]
    for df in frames[1:]:
        overlap = [c for c in df.columns
                   if c in merged.columns and c not in ("コード", "銘柄名", "市場")]
        merged = merged.merge(df.drop(columns=overlap),
                              on=["コード", "銘柄名", "市場"], how="outer")
    # TOPIX 500 (JPX 規模区分 Core30 + Large70 + Mid400 = 496銘柄) に絞る
    merged = filter_to_topix500(merged)
    merged = refresh_with_yfinance(merged, drop_no_parquet=True)

    eps   = pd.to_numeric(merged["EPS(一株あたり当期利益)"],     errors="coerce")
    eps_f = pd.to_numeric(merged["EPS(予)(一株あたり当期利益)"], errors="coerce")
    price = pd.to_numeric(merged["現在値"], errors="coerce")
    merged["PER"]    = price / eps_f.where(eps_f > 0)
    growth = ((eps_f - eps) / eps.abs()) * 100
    growth = growth.where(eps > 0)
    merged["成長率%"] = growth
    merged["PEG"]    = merged["PER"] / growth.where(growth > 0)
    merged["ROE"]    = pd.to_numeric(merged["ROE(自己資本利益率)"], errors="coerce")
    merged = apply_master_names(merged)
    return merged


# 主要銘柄リスト（日経225 Core30 中心）
_MAJOR_CODES = [
    "7203", "7974", "6861", "8035", "9983",
    "6098", "4063", "8306", "8316", "9433",
    "9432", "6981", "6501", "4519", "6902",
]
# 銘柄名は price_targets.csv の短縮形を使う（記事本文の表記と統一）
_name_map = load_price_targets_names()
MAJORS = [(code, _name_map.get(code, code)) for code in _MAJOR_CODES]

OIL_REFINING = [
    (code, _name_map.get(code, code))
    for code in ("5020", "5019", "5021")
]


def quadrant_color(peg, roe, peg_th=1.0, roe_th=10.0) -> str:
    if pd.isna(peg) or pd.isna(roe):
        return C_NEUTRAL
    if peg <= peg_th and roe >= roe_th:
        return C_GARP_IDEAL
    if peg > peg_th and roe >= roe_th:
        return C_GROWTH
    if peg <= peg_th and roe < roe_th:
        return C_VALUE
    return C_INVALID


# ════════════════════════════════════════════════════════════════════════
# 図1: GARPマップ全体 + 主要銘柄ハイライト
# ════════════════════════════════════════════════════════════════════════
# ラベルの手動オフセット（重なり回避）
# キーは銘柄名、値は (dx, dy) ピクセル。引き出し線をつけて散らす銘柄も指定する。
_LABEL_OFFSETS = {
    # ROE=10 ライン上の密集帯
    "三井住友":   (-60, 22),    # 左上
    "信越化":     (-50, -32),   # 左下
    "トヨタ":     (-30, -45),   # 下に長く引き出し
    # ROE=8-9 帯
    "村田製":     (-10, 55),    # 真上に長く引き出し
    "デンソー":   (35,  -25),   # 右下
    # ROE 13-14 帯
    "日 立":      (30,  30),    # 右上に少し離して
    "ＫＤＤＩ":   (-55, 12),    # 左
    # 右上の比較的離れた銘柄
    "リクルートＨＤ": (12,  6),
    "中外薬":     (14,  6),
    "東エレク":   (-12, 18),
}
# 引き出し線を付ける銘柄
_LABEL_WITH_LINE = {
    "三井住友", "信越化", "トヨタ", "村田製", "デンソー", "ＫＤＤＩ", "日 立",
}


def make_garp_map(df: pd.DataFrame, out_path: Path):
    fig, ax = plt.subplots(figsize=(13, 8))

    # 全銘柄（背景の薄いドット）
    bg = df.dropna(subset=["PEG", "ROE"]).copy()
    bg = bg[(bg["PEG"] > 0) & (bg["PEG"] <= 3.0) & (bg["ROE"] > -5) & (bg["ROE"] <= 50)]
    ax.scatter(bg["PEG"], bg["ROE"],
               s=18, color=C_NEUTRAL, alpha=0.35, edgecolors="none", zorder=1)

    # TOPIX 大型 100 銘柄 = Core30 + Large70 (中サイズ・薄青、ラベルなし。MAJORS と重ねるので少し下のレイヤ)
    universe_codes = topix_large100_codes()
    majors_codes = {c for c, _n in MAJORS}
    universe_only = bg[bg["コード"].isin(universe_codes - majors_codes)]
    ax.scatter(universe_only["PEG"], universe_only["ROE"],
               s=46, color="#7eaee0", alpha=0.55, edgecolors="white", linewidth=0.6,
               zorder=3, label="TOPIX 大型 100 銘柄")

    # 4象限の塗り（GARP理想ゾーンを強調）
    ax.axhspan(10, 60, xmin=0, xmax=1/3,
               facecolor=C_GARP_IDEAL, alpha=0.07, zorder=0)

    # 基準線
    ax.axvline(1.0, color="#999999", linestyle="--", linewidth=1.2, alpha=0.6, zorder=2)
    ax.axhline(10.0, color="#999999", linestyle="--", linewidth=1.2, alpha=0.6, zorder=2)

    # 主要銘柄を強調プロット
    df_idx = df.set_index("コード")
    off_majors = []  # 範囲外銘柄リスト（注釈用）
    for code, name in MAJORS:
        if code not in df_idx.index:
            continue
        row = df_idx.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        peg, roe = row.get("PEG"), row.get("ROE")
        if pd.isna(peg) or pd.isna(roe):
            continue
        if not (0 < peg <= 3.0):
            off_majors.append((name, peg, roe))
            continue
        c = quadrant_color(peg, roe)
        ax.scatter(peg, roe, s=200, color=c, edgecolor="white",
                   linewidth=2.0, zorder=5)
        dx, dy = _LABEL_OFFSETS.get(name, (10, 8))
        arrow = dict(arrowstyle="-", color=C_TEXT_SUB, lw=0.7,
                     shrinkA=0, shrinkB=4) if name in _LABEL_WITH_LINE else None
        ax.annotate(name, xy=(peg, roe), xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=16, color=C_TEXT, fontweight="bold", zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none",
                              alpha=0.85, boxstyle="round,pad=0.25"),
                    arrowprops=arrow)

    # ゾーンラベル
    ax.text(0.5, 55, "★ GARP 理想ゾーン", ha="center", va="top",
            fontsize=18, color=C_GARP_IDEAL, fontweight="bold")
    ax.text(2.0, 55, "割高グロース", ha="center", va="top",
            fontsize=16, color=C_GROWTH)
    ax.text(0.5, -2.5, "バリュー候補 (低ROE)", ha="center", va="top",
            fontsize=16, color=C_VALUE)
    ax.text(2.0, -2.5, "投資不適格", ha="center", va="top",
            fontsize=16, color=C_INVALID)

    # 範囲外銘柄の注釈（x軸ラベルの下、tight_layout に認識させる）
    if off_majors:
        note = "※ PEG > 3.0 で図外: " + "  ".join(
            f"{n} (PEG={p:.1f})" for n, p, _r in off_majors
        )
        ax.annotate(note, xy=(0.5, -0.13), xycoords="axes fraction",
                    fontsize=16, color=C_TEXT_SUB, va="top", ha="center")

    ax.set_xlim(0, 3.0)
    ax.set_ylim(-5, 60)
    ax.set_xlabel("PEG（予）  ← 割安   割高 →", fontsize=17, color=C_TEXT_SUB)
    ax.set_ylabel("ROE（%）  ← 低収益   高収益 →", fontsize=17, color=C_TEXT_SUB)
    ax.set_title("PEG × ROE GARP マップ — TOPIX 500 + 大型100 + 主要 15 社ハイライト",
                 fontsize=21, color=C_TEXT, fontweight="bold", pad=22)
    ax.grid(True, color=C_GRID, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=C_TEXT_SUB)

    # 凡例（手動で 3 要素のみ表示）
    legend_handles = [
        Line2D([], [], marker="o", linestyle="", color=C_NEUTRAL,
               markersize=5, markeredgecolor="none", alpha=0.55,
               label="TOPIX 500（PEG≤3 / ROE 範囲内）"),
        Line2D([], [], marker="o", linestyle="", color="#7eaee0",
               markersize=8, markeredgecolor="white",
               label="TOPIX 大型 100 銘柄（Core30 + Large70）"),
        Line2D([], [], marker="o", linestyle="", color=C_GARP_IDEAL,
               markersize=11, markeredgecolor="white",
               label="主要 15 社（ラベル付き、GARP 理想ゾーン）"),
    ]
    ax.legend(handles=legend_handles, loc="upper right",
              fontsize=16, framealpha=0.85, edgecolor="none")

    fig.tight_layout()

    _savefig_vpad(fig, out_path)
    plt.close(fig)
    print(f"  → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
# 図2: 主要銘柄 GARP スコアテーブル
# ════════════════════════════════════════════════════════════════════════
def make_majors_table(df: pd.DataFrame, out_path: Path):
    df_idx = df.set_index("コード")
    rows = []
    for code, name in MAJORS:
        if code not in df_idx.index:
            continue
        row = df_idx.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        peg = row.get("PEG")
        roe = row.get("ROE")
        per = row.get("PER")
        grw = row.get("成長率%")
        price = row.get("現在値")
        rows.append({
            "コード": code, "銘柄": name, "株価": price,
            "PER": per, "成長率%": grw, "PEG": peg, "ROE": roe,
            "GARP_raw": (roe / peg) if (pd.notna(peg) and pd.notna(roe) and peg > 0) else np.nan,
        })
    tbl = pd.DataFrame(rows)
    # GARPスコア（フィルタユニバース全体での Min-Max ではなく、本表内での 0〜100 化）
    valid = tbl["GARP_raw"].dropna()
    if not valid.empty and valid.max() > valid.min():
        tbl["GARPスコア"] = (tbl["GARP_raw"] - valid.min()) / (valid.max() - valid.min()) * 100
    else:
        tbl["GARPスコア"] = np.nan
    tbl = tbl.sort_values("GARPスコア", ascending=False, na_position="last").reset_index(drop=True)

    # 描画
    fig, ax = plt.subplots(figsize=(13, 0.60 * len(tbl) + 1.73))
    ax.axis("off")

    # ヘッダ
    headers = ["銘柄", "コード", "株価", "PER", "成長率%", "PEG", "ROE%", "GARPスコア"]
    col_x = [0.02, 0.26, 0.39, 0.49, 0.59, 0.67, 0.76, 0.90]
    aligns = ["left", "right", "right", "right", "right", "right", "right", "right"]

    y_top = 1.0
    row_h = 1.0 / (len(tbl) + 2.2)

    # タイトル
    ax.text(0.5, y_top + row_h * 0.5,
            "主要銘柄の GARP スコア — 本表内で 0〜100 に正規化",
            ha="center", va="bottom",
            fontsize=21, color=C_TEXT, fontweight="bold", transform=ax.transAxes)

    # ヘッダ行
    for x, h, al in zip(col_x, headers, aligns):
        ax.text(x, y_top - row_h * 0.7, h, ha=al, va="center",
                fontsize=16, color=C_TEXT_SUB, fontweight="bold",
                transform=ax.transAxes)
    ax.plot([0.02, 0.98], [y_top - row_h * 1.2, y_top - row_h * 1.2],
            color=C_GRID, linewidth=1.2, transform=ax.transAxes)

    # データ行
    for i, r in tbl.iterrows():
        y = y_top - row_h * (i + 2.0)
        # GARPスコア背景バー
        score = r["GARPスコア"]
        if pd.notna(score):
            bar_w = (score / 100) * 0.10
            color = quadrant_color(r["PEG"], r["ROE"])
            ax.add_patch(plt.Rectangle(
                (col_x[7] - 0.005, y - row_h * 0.35),
                bar_w, row_h * 0.7,
                facecolor=color, alpha=0.35, edgecolor="none",
                transform=ax.transAxes,
            ))
        vals = [
            r["銘柄"], r["コード"],
            f"{r['株価']:,.0f}" if pd.notna(r["株価"]) else "—",
            f"{r['PER']:.1f}" if pd.notna(r["PER"]) else "—",
            f"{r['成長率%']:+.1f}" if pd.notna(r["成長率%"]) else "—",
            f"{r['PEG']:.2f}" if pd.notna(r["PEG"]) else "—",
            f"{r['ROE']:.1f}" if pd.notna(r["ROE"]) else "—",
            f"{score:.0f}" if pd.notna(score) else "—",
        ]
        weights = ["bold"] + ["normal"] * 6 + ["bold"]
        colors  = [C_TEXT] + [C_TEXT_SUB] + [C_TEXT] * 5 + [C_TEXT]
        for x, v, al, w, c in zip(col_x, vals, aligns, weights, colors):
            ax.text(x, y, v, ha=al, va="center",
                    fontsize=16, color=c, fontweight=w, transform=ax.transAxes)


    _savefig_vpad(fig, out_path)
    plt.close(fig)
    print(f"  → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
# 図3: 石油元売3社の GARP 位置 + 指標カード
# ════════════════════════════════════════════════════════════════════════
def make_oil_card(df: pd.DataFrame, out_path: Path):
    df_idx = df.set_index("コード")

    fig = plt.figure(figsize=(13, 6.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.4, 1.0], wspace=0.18,
                          left=0.06, right=0.97, top=0.88, bottom=0.03)

    # 左: GARPマップ拡大
    ax = fig.add_subplot(gs[0, 0])
    bg = df.dropna(subset=["PEG", "ROE"]).copy()
    bg = bg[(bg["PEG"] > 0) & (bg["PEG"] <= 2.0) & (bg["ROE"] > -5) & (bg["ROE"] <= 30)]
    ax.scatter(bg["PEG"], bg["ROE"], s=14, color=C_NEUTRAL, alpha=0.30, edgecolors="none")

    ax.axvline(1.0, color="#999999", linestyle="--", linewidth=1.2, alpha=0.6)
    ax.axhline(10.0, color="#999999", linestyle="--", linewidth=1.2, alpha=0.6)

    for code, name in OIL_REFINING:
        if code not in df_idx.index:
            continue
        row = df_idx.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        peg, roe = row.get("PEG"), row.get("ROE")
        if pd.isna(peg) or pd.isna(roe) or not (0 < peg <= 2.0):
            continue
        c = quadrant_color(peg, roe)
        ax.scatter(peg, roe, s=320, color=c, edgecolor="white", linewidth=2.5, zorder=5)
        ax.annotate(name, xy=(peg, roe), xytext=(12, 8),
                    textcoords="offset points",
                    fontsize=17, color=C_TEXT, fontweight="bold")

    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 20)
    ax.set_xlabel("PEG（予）", fontsize=16, color=C_TEXT_SUB)
    ax.set_ylabel("ROE（%）", fontsize=16, color=C_TEXT_SUB)
    # サブタイトルは suptitle に統合（ax.set_title は suptitle と重なるため除去）
    ax.grid(True, color=C_GRID, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=C_TEXT_SUB)

    # 右: 指標カード
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    card_h = 0.32   # フォント 16-18pt に合わせて拡大（旧 0.28）
    card_gap = 0.02  # カード間隔（旧 0.04）。3枚合計 = 3*0.32+2*0.02 = 1.00
    y_start = 1.0
    for i, (code, name) in enumerate(OIL_REFINING):
        y0 = y_start - (i + 1) * card_h - i * card_gap
        if code not in df_idx.index:
            continue
        row = df_idx.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        peg = row.get("PEG")
        roe = row.get("ROE")
        per = row.get("PER")
        price = row.get("現在値")
        c = quadrant_color(peg, roe)
        # カード枠
        ax2.add_patch(FancyBboxPatch(
            (0.02, y0), 0.96, card_h,
            boxstyle="round,pad=0.01,rounding_size=0.018",
            facecolor="white", edgecolor="none", linewidth=0,
            transform=ax2.transAxes,
        ))
        # 銘柄名
        ax2.text(0.08, y0 + card_h * 0.80, name,
                 fontsize=18, color=C_TEXT, fontweight="bold", transform=ax2.transAxes)
        # コードと指標ラベルを同じ行に配置
        ax2.text(0.08, y0 + card_h * 0.56, f"{code}",
                 fontsize=16, color=C_TEXT_SUB, transform=ax2.transAxes)
        # 指標
        items = [
            ("PEG", f"{peg:.2f}" if pd.notna(peg) else "—"),
            ("ROE", f"{roe:.1f}%" if pd.notna(roe) else "—"),
            ("PER", f"{per:.1f}" if pd.notna(per) else "—"),
            ("株価", f"{price:,.0f}円" if pd.notna(price) else "—"),
        ]
        xs = [0.34, 0.50, 0.68, 0.84]
        for x, (label, val) in zip(xs, items):
            ax2.text(x, y0 + card_h * 0.56, label,
                     fontsize=16, color=C_TEXT_SUB,
                     ha="center", transform=ax2.transAxes)
            ax2.text(x, y0 + card_h * 0.24, val,
                     fontsize=17, color=C_TEXT, fontweight="bold",
                     ha="center", transform=ax2.transAxes)

    fig.suptitle("石油元売3社の GARP 比較 — コスモのみ理想ゾーン",
                 fontsize=21, color=C_TEXT, fontweight="bold", y=0.97)


    _savefig_vpad(fig, out_path)
    plt.close(fig)
    print(f"  → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
# 株価チャート生成 共通
# ════════════════════════════════════════════════════════════════════════
def load_close(code: str, months: int = 6) -> pd.Series:
    p = PRICES_STOCKS_DAILY / f"{code}.parquet"
    if not p.exists():
        return pd.Series(dtype="float64")
    df = pd.read_parquet(p, columns=["Close"])
    df.index = pd.to_datetime(df.index)
    cutoff = df.index[-1] - pd.DateOffset(months=months)
    return df.loc[df.index >= cutoff, "Close"].dropna()


def _draw_minichart(ax, s: pd.Series, name: str, code: str,
                    peg, roe, color: str):
    if s.empty:
        ax.text(0.5, 0.5, "データ無し", ha="center", va="center",
                color=C_TEXT_SUB, transform=ax.transAxes)
        ax.axis("off")
        return
    # 期間騰落率
    chg = (s.iloc[-1] / s.iloc[0] - 1) * 100
    line_c = "#1a9f3c" if chg >= 0 else "#e8372c"

    # 塗り
    ymin = float(s.min())
    ymax = float(s.max())
    pad = (ymax - ymin) * 0.10
    floor = ymin - pad
    ax.fill_between(s.index, s.values, floor, color=line_c, alpha=0.08)
    ax.plot(s.index, s.values, color=line_c, linewidth=1.6)

    ax.set_ylim(floor, ymax + pad)
    ax.set_xlim(s.index[0], s.index[-1])
    ax.grid(True, color=C_GRID, linewidth=0.6, axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # X軸: 月初を主要目盛とし「m月」ラベルを表示（プラットフォーム非依存）
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x, _: f"{mdates.num2date(x).month}月"))
    ax.tick_params(left=False, labelleft=False,
                   labelbottom=True, bottom=False,
                   labelsize=16, colors=C_TEXT_SUB, pad=2)

    # 銘柄ラベル
    ax.text(0.02, 0.95, name, fontsize=16, color=C_TEXT,
            fontweight="bold", ha="left", va="top", transform=ax.transAxes)
    ax.text(0.02, 0.82, f"{code}", fontsize=16, color=C_TEXT_SUB,
            ha="left", va="top", transform=ax.transAxes)

    # 騰落率（右上）
    ax.text(0.98, 0.95, f"{chg:+.1f}%",
            fontsize=16, color=line_c, fontweight="bold",
            ha="right", va="top", transform=ax.transAxes)
    # GARP指標（右下）
    peg_str = f"PEG {peg:.2f}" if pd.notna(peg) else "PEG —"
    roe_str = f"ROE {roe:.1f}%" if pd.notna(roe) else "ROE —"
    ax.text(0.98, 0.04, f"{peg_str}   {roe_str}",
            fontsize=16, color=C_TEXT_SUB,
            ha="right", va="bottom", transform=ax.transAxes)

    # GARPゾーンドット
    ax.scatter([0.04], [0.06], s=80, color=color, transform=ax.transAxes,
               clip_on=False, edgecolor="white", linewidth=1.0)


def make_charts_grid(df: pd.DataFrame, codes: list[tuple[str, str]],
                     out_path: Path, title: str,
                     cols: int = 5, months: int = 6,
                     col_w: float = 3.4,
                     row_h: float = 2.6):
    df_idx = df.set_index("コード")
    n = len(codes)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols,
                             figsize=(cols * col_w, rows * row_h + 1.0))
    if rows == 1 and cols == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = np.array([axes])
    elif cols == 1:
        axes = np.array([[a] for a in axes])

    for i, (code, name) in enumerate(codes):
        r, c = divmod(i, cols)
        ax = axes[r][c]
        s = load_close(code, months=months)
        if code in df_idx.index:
            row = df_idx.loc[code]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            peg, roe = row.get("PEG"), row.get("ROE")
        else:
            peg, roe = np.nan, np.nan
        color = quadrant_color(peg, roe)
        _draw_minichart(ax, s, name, code, peg, roe, color)
    # 空のセルを非表示
    for i in range(n, rows * cols):
        r, c = divmod(i, cols)
        axes[r][c].axis("off")

    fig.suptitle(title, fontsize=21, color=C_TEXT, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.0, left=0.03, right=0.97,
                        hspace=0.30, wspace=0.18)

    _savefig_vpad(fig, out_path)
    plt.close(fig)
    print(f"  → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
# main
# ════════════════════════════════════════════════════════════════════════
def main():
    print("データロード中...")
    df = load_universe()
    print(f"  ユニバース: {len(df):,} 銘柄")

    print("画像生成中...")
    make_garp_map(df, OUT_DIR / "01_garp_map.png")
    make_majors_table(df, OUT_DIR / "02_majors_table.png")
    make_oil_card(df, OUT_DIR / "03_oil_refining.png")
    make_charts_grid(df, MAJORS, OUT_DIR / "04_majors_charts.png",
                     "主要銘柄 — 直近 6ヶ月 の株価チャート（左下ドット = GARPゾーン色）",
                     cols=5, months=6, col_w=3.4, row_h=2.6)
    make_charts_grid(df, OIL_REFINING, OUT_DIR / "05_oil_charts.png",
                     "石油元売3社 — 直近 6ヶ月 の株価チャート（左下ドット = GARPゾーン色）",
                     cols=3, months=6, col_w=4.5, row_h=3.0)
    print(f"\n保存先: {OUT_DIR}")


if __name__ == "__main__":
    main()
