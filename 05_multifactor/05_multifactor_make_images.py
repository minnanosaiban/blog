"""
blog/02_マルチファクタースコアボード.md 用の画像生成スクリプト。

生成画像:
  01_scoreboard_top20.png       — 総合スコア Top20 のヒートマップ表
  02_factor_distribution.png    — 7 ファクターのスコア分布ヒストグラム
  03_value_quality_scatter.png  — Value × Quality 散布図 + 主要銘柄ハイライト
  04_majors_radar.png           — 主要 6 社の 7 ファクターレーダー
  05_oil_refining_factors.png   — 石油元売 3 社の 7 ファクター比較レーダー + 横棒

実行: python scripts/blog/05_multifactor_scoreboard_make_images.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Rectangle

from config.paths import rakunav_file, PRICES_STOCKS_DAILY
from utils.universe_topix500 import filter_to_topix500, topix_large100_codes
from utils.price_metrics import compute_price_metrics
from utils.master_names import apply_master_names, load_price_targets_names


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

FACTOR_COLORS = {
    "Value":     "#4C8BF5",
    "Quality":   "#50C878",
    "Growth":    "#F5A623",
    "Consensus": "#888888",
    "Sentiment": "#E05C5C",
    "Momentum":  "#999999",
    "Risk":      "#8C8C8C",
}
FACTORS = list(FACTOR_COLORS)
C_TEXT     = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID     = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/05_multifactor_scoreboard")
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
RAKUNAV_SPECS = [
    (113, "EPS(一株あたり当期利益)", "EPS実績"),
    (215, "BPS(予)(一株あたり純資産)", "BPS予"),
    (141, "配当金(円)", "配当金"),
    (133, "EV/EBITDA倍率", "EV/EBITDA"),
    (118, "ROE(自己資本利益率)", "ROE"),
    (119, "ROA(総資産当期利益率)", "ROA"),
    (125, "売上高営業利益率", "営業利益率"),
    (130, "自己資本比率", "自己資本比率"),
    (122, "売上高変化率", "売上高変化率"),
    (129, "経常利益変化率", "経常利益変化率"),
    (219, "過去3年平均売上高成長率(予)", "過去3年平均売上高成長率(予)"),
    (220, "業績予想修正率(予)", "業績予想修正率(予)"),
    (221, "経常利益変化率(予)", "経常利益変化率(予)"),
]

FACTOR_DEFS = {
    "Value":     [("PER", False), ("PBR", False), ("EV/EBITDA", False), ("配当利回り", True)],
    "Quality":   [("ROE", True), ("ROA", True), ("営業利益率", True), ("自己資本比率", True)],
    "Growth":    [("売上高変化率", True), ("経常利益変化率", True)],
    "Consensus": [("業績予想修正率(予)", True), ("経常利益変化率(予)", True),
                  ("過去3年平均売上高成長率(予)", True)],
    "Sentiment": [("出来高増加率", True), ("売買代金増加率", True)],
    "Momentum":  [("値上り率", True), ("過去52週安値からの上昇率", True),
                  ("株価移動平均線からの乖離率①", True)],
    "Risk":      [("過去60日ボラティリティ", False), ("ベータ(対日経平均)", False)],
}


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
    # rakunav 13 指標を統合
    merged = None
    for no, vc, oc in RAKUNAV_SPECS:
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.strip()
        cand = [c for c in df.columns if c == vc or c.startswith(vc)]
        df[oc] = df[cand[0]].map(_to_float)
        d = df[["コード", "銘柄名", "市場", oc]]
        merged = d if merged is None else merged.merge(d, on=["コード", "銘柄名", "市場"], how="outer")

    # TOPIX 500 (JPX 規模区分 Core30 + Large70 + Mid400 = 496銘柄) に絞る
    merged = filter_to_topix500(merged)

    # 最新終値
    rows = []
    for p in PRICES_STOCKS_DAILY.glob("*.parquet"):
        try:
            s = pd.read_parquet(p, columns=["Close"])["Close"].dropna()
            if not s.empty:
                rows.append({"コード": p.stem, "Close_yf": float(s.iloc[-1])})
        except Exception:
            pass
    closes = pd.DataFrame(rows)
    merged = merged.merge(closes, on="コード", how="inner")

    # Value 自前計算
    merged["PER"]       = merged["Close_yf"] / merged["EPS実績"].where(merged["EPS実績"] > 0)
    merged["PBR"]       = merged["Close_yf"] / merged["BPS予"].where(merged["BPS予"] > 0)
    merged["配当利回り"] = merged["配当金"].where(merged["配当金"] > 0) / merged["Close_yf"] * 100

    # 価格・出来高指標
    pm = compute_price_metrics(merged["コード"].tolist())
    merged = merged.merge(pm, on="コード", how="left")

    # 銘柄名を price_targets の短縮表記に統一
    merged = apply_master_names(merged)
    return merged


def percentile_score(series: pd.Series, higher_better: bool) -> pd.Series:
    ranked = series.rank(pct=True, na_option="keep") * 100
    if not higher_better:
        ranked = 100 - ranked
    return ranked.fillna(50)


def add_factor_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for factor, metrics in FACTOR_DEFS.items():
        cols = []
        for col, higher in metrics:
            if col not in out.columns:
                continue
            series = out[col].where(out[col] > 0) if not higher else out[col]
            sc = f"_s_{col}"
            out[sc] = percentile_score(series, higher)
            cols.append(sc)
        out[f"score_{factor}"] = out[cols].mean(axis=1) if cols else 50.0
    out["score_総合"] = out[[f"score_{f}" for f in FACTORS]].mean(axis=1)
    return out


# 主要銘柄（連載01 と同じ 6 社で揃える）
# 銘柄名は price_targets.csv の短縮形を使う（記事本文の表記と統一）
_MAJOR_CODES_02 = ["7203", "9984", "6758", "8306", "6861", "9433"]
_name_map_02 = load_price_targets_names()
MAJORS = [(code, _name_map_02.get(code, code)) for code in _MAJOR_CODES_02]

# 連載01 と同じ石油元売 3 社（セクター内比較）
OIL_REFINERS = [
    ("5021", _name_map_02.get("5021", "コスモエネＨＤ"), "#888888"),
    ("5020", _name_map_02.get("5020", "ＥＮＥＯＳ"),     "#444444"),
    ("5019", _name_map_02.get("5019", "出光興産"),       "#aaaaaa"),
]


# ── 1) Top20 スコアボード ──────────────────────────────────────────────────
def make_scoreboard_top20(df: pd.DataFrame) -> None:
    # スコア計算は TOPIX 500 全体だが、Top 20 表示は TOPIX 大型 100 銘柄 (Core30+Large70) 内に絞る
    # （読者層: 大型・有名株中心の投資家。中小型発掘よりも知名度のある銘柄の序列）
    universe = topix_large100_codes()
    pool = df[df["コード"].isin(universe)]
    top = pool.nlargest(20, "score_総合").reset_index(drop=True)
    top.index += 1
    cols = ["score_総合"] + [f"score_{f}" for f in FACTORS]

    fig, ax = plt.subplots(figsize=(13, 7.9))
    ax.set_xlim(-0.5, 5.5 + len(cols) - 0.3)
    ax.set_ylim(len(top) + 1, -1)

    # ヘッダ
    ax.text(0.0, -0.5, "順位", fontsize=16, fontweight="bold", ha="center", va="center", color=C_TEXT)
    ax.text(1.0, -0.5, "コード", fontsize=16, fontweight="bold", ha="center", va="center", color=C_TEXT)
    ax.text(2.5, -0.5, "銘柄名", fontsize=16, fontweight="bold", ha="left",   va="center", color=C_TEXT)
    abbr = {"Value": "Value", "Quality": "Qual.", "Growth": "Growth",
            "Consensus": "Cons.", "Sentiment": "Sent.", "Momentum": "Mom.", "Risk": "Risk"}
    abbr_labels = ["総合"] + [abbr[f] for f in FACTORS]
    for i, lab in enumerate(abbr_labels):
        ax.text(5.5 + i, -0.5, lab, fontsize=16, fontweight="bold",
                ha="center", va="center", color=C_TEXT)

    cmap = plt.get_cmap("RdYlGn")
    for r, (_, row) in enumerate(top.iterrows()):
        ax.text(0.0, r + 0.5, f"{r+1}",   fontsize=16, ha="center", va="center", color=C_TEXT)
        ax.text(1.0, r + 0.5, row["コード"], fontsize=16, ha="center", va="center", color=C_TEXT)
        name = (row["銘柄名"] or "")[:14]
        ax.text(2.5, r + 0.5, name, fontsize=16, ha="left", va="center", color=C_TEXT)
        for i, col in enumerate(cols):
            v = row[col]
            color = cmap(np.clip(v / 100, 0.05, 0.95))
            rect = Rectangle((5.5 + i - 0.45, r + 0.05), 0.9, 0.9,
                             facecolor=color, edgecolor="white", linewidth=1.0)
            ax.add_patch(rect)
            txt_color = "white" if v < 35 or v > 70 else "#202124"
            ax.text(5.5 + i, r + 0.5, f"{v:.0f}",
                    fontsize=16, ha="center", va="center",
                    color=txt_color, fontweight="bold" if col == "score_総合" else "normal")

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_title("総合スコア Top 20  ―  TOPIX 大型 100 銘柄 × 7 ファクター ヒートマップ",
                 fontsize=18, fontweight="bold", color=C_TEXT, pad=22, loc="left")

    _savefig_vpad(fig, OUT_DIR / "01_scoreboard_top20.png")
    plt.close(fig)


# ── 2) ファクタースコア分布 ─────────────────────────────────────────────────
def make_factor_distribution(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.8))
    axes = axes.flatten()
    # 低/中/高スコア帯ごとの色（落ち着いたトーン）
    ZONE_LOW    = "#c98686"  # 0-30   ダスティローズ（不調）
    ZONE_MID    = "#d8d8d8"  # 30-70  ライトグレー（中立）
    ZONE_HIGH   = "#8ab09a"  # 70-100 セージグリーン（好調）
    bins = np.linspace(0, 100, 21)  # 20 ビン、幅 5
    for i, f in enumerate(FACTORS):
        ax = axes[i]
        s = df[f"score_{f}"].dropna()
        counts, _ = np.histogram(s, bins=bins)
        colors = []
        for left, right in zip(bins[:-1], bins[1:]):
            mid = (left + right) / 2
            if mid < 30:
                colors.append(ZONE_LOW)
            elif mid < 70:
                colors.append(ZONE_MID)
            else:
                colors.append(ZONE_HIGH)
        ax.bar(bins[:-1], counts, width=np.diff(bins),
               color=colors, align="edge", alpha=0.75,
               edgecolor="white", linewidth=0.5)
        med = float(s.median())
        ax.axvline(med, color="#202124", linestyle="--", linewidth=1.0, alpha=0.5)
        ax.text(med + 1.5, ax.get_ylim()[1] * 0.92, f"中央{med:.0f}",
                fontsize=16, color="#202124")
        ax.set_title(f, fontsize=16, fontweight="bold", color=C_TEXT)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 50, 100])
        ax.tick_params(labelsize=16, colors=C_TEXT_SUB)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)
    # 余ったセルを消す（7ファクター → 8セル中 1つ余る）
    for ax in axes[len(FACTORS):]:
        ax.axis("off")

    fig.suptitle(f"7 ファクター スコア分布（対象 {len(df):,} 銘柄）",
                 fontsize=18, fontweight="bold", color=C_TEXT, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    _savefig_vpad(fig, OUT_DIR / "02_factor_distribution.png")
    plt.close(fig)


# ── 3) Value × Quality 散布図 ─────────────────────────────────────────────
def make_value_quality_scatter(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 9.0))

    # 4 象限の薄塗り
    ax.axhspan(70, 100, xmin=0.7, xmax=1.0, facecolor="#5a9a72", alpha=0.08)  # 右上 ★Buffett
    ax.axhspan(70, 100, xmin=0.0, xmax=0.3, facecolor="#3498db", alpha=0.05)  # 左上 高品質グロース
    ax.axhspan(0,  30,  xmin=0.7, xmax=1.0, facecolor="#c87878", alpha=0.05)  # 右下 バリュー罠

    # 全銘柄背景
    base = df.dropna(subset=["score_Value", "score_Quality"])
    ax.scatter(base["score_Value"], base["score_Quality"],
               s=10, color="#bbbbbb", alpha=0.30, edgecolors="none", zorder=1)

    # 主要銘柄
    for code, _label_hint in MAJORS:
        row = df.loc[df["コード"] == code]
        if row.empty:
            continue
        r = row.iloc[0]
        label = r["銘柄名"]
        ax.scatter(r["score_Value"], r["score_Quality"],
                   s=180, color="#999999", edgecolor="white", linewidth=2.0, zorder=5)
        ax.annotate(label, xy=(r["score_Value"], r["score_Quality"]),
                    xytext=(10, 8), textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    bbox=dict(facecolor="white", alpha=0.88,
                              edgecolor="none", boxstyle="round,pad=0.25"))

    # 基準線
    ax.axhline(70, color="#5a9a72", linestyle="--", alpha=0.5, linewidth=1.0)
    ax.axvline(70, color="#5a9a72", linestyle="--", alpha=0.5, linewidth=1.0)
    ax.axhline(50, color="#cccccc", linestyle=":",  alpha=0.6, linewidth=0.8)
    ax.axvline(50, color="#cccccc", linestyle=":",  alpha=0.6, linewidth=0.8)

    # ゾーンラベル
    ax.text(85, 92, "★クオリティ・バリュー\n（バフェット流）",
            fontsize=16, fontweight="bold", color="#5a9a72",
            ha="center", va="center")
    ax.text(15, 92, "高品質グロース\n（割高優良）", fontsize=16, color="#3498db",
            ha="center", va="center")
    ax.text(85, 12, "バリュー・トラップ警戒", fontsize=16, color="#c87878",
            ha="center", va="center")
    ax.text(15, 12, "低品質×割高\n（投資不適格）", fontsize=16, color="#888888",
            ha="center", va="center")

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Value スコア  ← 割高     割安 →", fontsize=16, color=C_TEXT)
    ax.set_ylabel("Quality スコア  ← 低品質    高品質 →", fontsize=16, color=C_TEXT)
    ax.set_title("Value × Quality 散布図  ―  4 ゾーンと主要銘柄の位置",
                 fontsize=18, fontweight="bold", color=C_TEXT, pad=22, loc="left")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    plt.tight_layout()

    _savefig_vpad(fig, OUT_DIR / "03_value_quality_scatter.png")
    plt.close(fig)


# ── 4) 主要銘柄レーダー ─────────────────────────────────────────────────────
def make_majors_radar(df: pd.DataFrame) -> None:
    n_majors = len(MAJORS)
    n_cols = 3
    n_rows = (n_majors + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(13, 4.8 * n_rows),
                             subplot_kw=dict(projection="polar"))
    axes = axes.flatten() if n_majors > 1 else [axes]

    angles = np.linspace(0, 2 * np.pi, len(FACTORS), endpoint=False).tolist()
    angles_closed = angles + [angles[0]]

    for i, (code, _label_hint) in enumerate(MAJORS):
        ax = axes[i]
        row = df.loc[df["コード"] == code]
        if row.empty:
            ax.axis("off")
            continue
        r = row.iloc[0]
        vals = [r[f"score_{f}"] for f in FACTORS]
        vals_closed = vals + [vals[0]]

        ax.fill(angles_closed, vals_closed, color="#666666", alpha=0.20)
        ax.plot(angles_closed, vals_closed, color="#666666", linewidth=2.0, marker="o", markersize=4)

        # 50 ライン
        ax.plot(angles_closed, [50] * len(angles_closed), color="#cccccc",
                linewidth=0.8, linestyle="--")

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75])
        ax.set_yticklabels(["25", "50", "75"], fontsize=16, color=C_TEXT_SUB)
        ax.set_xticks(angles)
        ax.set_xticklabels(FACTORS, fontsize=16, color=C_TEXT)

        total = r["score_総合"]
        label = r["銘柄名"]
        ax.set_title(f"{label}（総合 {total:.0f}）",
                     fontsize=16, fontweight="bold", color=C_TEXT, pad=22)

    for ax in axes[n_majors:]:
        ax.axis("off")

    fig.suptitle("主要 6 社の 7 ファクターレーダー",
                 fontsize=18, fontweight="bold", color=C_TEXT, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.subplots_adjust(hspace=0.55)

    _savefig_vpad(fig, OUT_DIR / "04_majors_radar.png")
    plt.close(fig)


# ── 5) 石油元売 3 社のセクター内比較 ────────────────────────────────────────
def make_oil_refining_compare(df: pd.DataFrame) -> None:
    """連載01 と同じ 3 社を 7 ファクター・レーダーで可視化。"""
    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1], wspace=0.35)

    angles = np.linspace(0, 2 * np.pi, len(FACTORS), endpoint=False).tolist()
    angles_closed = angles + [angles[0]]

    for i, (code, _label_hint, color) in enumerate(OIL_REFINERS):
        ax = fig.add_subplot(gs[0, i], projection="polar")
        row = df.loc[df["コード"] == code]
        if row.empty:
            ax.axis("off")
            continue
        r = row.iloc[0]
        label = r["銘柄名"]
        vals = [r[f"score_{f}"] for f in FACTORS]
        vals_closed = vals + [vals[0]]

        ax.fill(angles_closed, vals_closed, color=color, alpha=0.22)
        ax.plot(angles_closed, vals_closed, color=color, linewidth=2.0, marker="o", markersize=4)
        ax.plot(angles_closed, [50] * len(angles_closed), color="#cccccc",
                linewidth=0.8, linestyle="--")

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75])
        ax.set_yticklabels(["25", "50", "75"], fontsize=16, color=C_TEXT_SUB)
        ax.set_xticks(angles)
        ax.set_xticklabels(FACTORS, fontsize=16, color=C_TEXT)
        ax.set_title(f"{label}\n（総合 {r['score_総合']:.0f}）",
                     fontsize=16, fontweight="bold", color=C_TEXT, pad=20)

    fig.suptitle("石油元売 3 社の 7 ファクター比較  ―  セクター内マルチファクター分析",
                 fontsize=18, fontweight="bold", color=C_TEXT, y=0.98)
    fig.subplots_adjust(top=0.88)

    _savefig_vpad(fig, OUT_DIR / "05_oil_refining_factors.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df_raw = load_universe()
    df = add_factor_scores(df_raw)
    print(f"[load] {len(df):,} 銘柄")
    print(f"[majors] " + ", ".join(
        f"{n}: 総合={df.loc[df['コード']==c, 'score_総合'].iloc[0]:.1f}"
        for c, n in MAJORS if (df['コード']==c).any()
    ))

    make_scoreboard_top20(df)
    print("[ok] 01_scoreboard_top20.png")
    make_factor_distribution(df)
    print("[ok] 02_factor_distribution.png")
    make_value_quality_scatter(df)
    print("[ok] 03_value_quality_scatter.png")
    make_majors_radar(df)
    print("[ok] 04_majors_radar.png")
    make_oil_refining_compare(df)
    print("[ok] 05_oil_refining_factors.png")

    # 連載02 用の分析用統計値も出力（記事執筆で参照）
    print("\n=== 分析用統計値 ===")
    n_all_60 = ((df[[f'score_{f}' for f in FACTORS]] >= 60).all(axis=1)).sum()
    n_trap   = ((df['score_Value'] >= 70) & (df['score_Quality'] <= 30)).sum()
    n_hot    = ((df['score_Momentum'] >= 90) & (df['score_Sentiment'] >= 90) & (df['score_Risk'] <= 20)).sum()
    n_qv     = ((df['score_Value'] >= 70) & (df['score_Quality'] >= 70)).sum()
    print(f"all-7-factors >= 60: {n_all_60} stocks")
    print(f"value-trap (Value>=70, Quality<=30): {n_trap} stocks")
    print(f"hot zone (Mom>=90, Sen>=90, Risk<=20): {n_hot} stocks")
    print(f"quality-value (V>=70 & Q>=70): {n_qv} stocks")

    # Top10 詳細（全ユニバース）
    print("\n=== 総合スコア Top10（TOPIX 500） ===")
    top10 = df.nlargest(10, "score_総合")[
        ["コード", "銘柄名", "市場", "score_総合"] + [f"score_{f}" for f in FACTORS]
    ]
    print(top10.to_string(index=False))

    # TOPIX 大型 100 銘柄内の Top 20（記事掲載対象）
    universe = topix_large100_codes()
    pool = df[df["コード"].isin(universe)]
    print(f"\n=== TOPIX 大型 100 内 Top 20（{len(pool)} 銘柄から抽出） ===")
    top20_universe = pool.nlargest(20, "score_総合")[
        ["コード", "銘柄名", "市場", "score_総合"] + [f"score_{f}" for f in FACTORS]
    ]
    print(top20_universe.to_string(index=False))
