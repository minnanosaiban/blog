"""
blog/04_連続サプライズスコアボード.md 用の画像生成スクリプト。

生成画像:
  01_surprise_top20.png       — サプライズスコア Top20 のヒートマップ表
  02_oil_refining_surprise.png — 石油元売 3 社の 3 シグナル比較
  03_revision_vs_ordprofit.png — 修正率 × 経常変化率(予) 4 象限散布図
  04_signal_overlap.png        — 単一シグナル Top10 vs 合成スコア Top10 のオーバーラップ
  05_signal_distribution.png   — 3 シグナルの分布ヒストグラム

実行: python scripts/blog/04_surprise_score_make_images.py
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

C_REV  = "#5a9a72"  # 緑: 修正率
C_EPS  = "#3498db"  # 青: EPS 予想超過率
C_ORD  = "#888888"  # 紫: 経常変化率
C_HOT  = "#c87878"  # 赤: 注目ゾーン
C_BG   = "#cccccc"
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/04_surprise")
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


# ── データ準備 ─────────────────────────────────────────────────────────────
RAKUNAV_SPECS = [
    (220, "業績予想修正率(予)",         "業績予想修正率(予)"),
    (213, "EPS(予)(一株あたり当期利益)", "EPS予"),
    (113, "EPS(一株あたり当期利益)",     "EPS実績"),
    (221, "経常利益変化率(予)",          "経常利益変化率(予)"),
    (118, "ROE(自己資本利益率)",         "ROE"),
    (120, "時価総額(百万円)",            "時価総額"),
]


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
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )

    # EPS 予想超過率
    safe_actual = merged["EPS実績"].where(merged["EPS実績"].abs() >= 1.0)
    merged["EPS予想超過率"] = ((merged["EPS予"] - safe_actual) / safe_actual.abs()) * 100

    merged = apply_master_names(merged)
    return merged


def percentile_score(series: pd.Series) -> pd.Series:
    return (series.rank(pct=True, na_option="keep") * 100).fillna(50)


def add_surprise_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_s_rev"] = percentile_score(out["業績予想修正率(予)"])
    out["_s_eps"] = percentile_score(out["EPS予想超過率"])
    out["_s_ord"] = percentile_score(out["経常利益変化率(予)"])
    out["サプライズスコア"] = out[["_s_rev", "_s_eps", "_s_ord"]].mean(axis=1)
    return out


OIL_REFINERS = [
    ("5021", "コスモエネＨＤ", "#888888"),
    ("5020", "ＥＮＥＯＳ",      "#444444"),
    ("5019", "出光興産",       "#aaaaaa"),
]


# ── 1) サプライズスコア Top20 ───────────────────────────────────────────────
def make_surprise_top20(df: pd.DataFrame) -> None:
    f = df[df["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]
    f = f[f["業績予想修正率(予)"].notna()]
    f = f[f["業績予想修正率(予)"] >= 0]
    top = f.nlargest(20, "サプライズスコア").reset_index(drop=True)
    top.index += 1

    fig, ax = plt.subplots(figsize=(13.5, 8.6))
    ax.set_xlim(-0.5, 11.7)
    ax.set_ylim(len(top) + 1, -1)

    # Header
    headers = [("順位", 0.0, "center"), ("コード", 1.0, "center"), ("銘柄名", 2.5, "left"),
               ("サプライズSC", 5.0, "center"),
               ("修正率(%)", 6.7, "center"),
               ("EPS超過率(%)", 8.2, "center"),
               ("経常変化率(予)(%)", 9.9, "center"),
               ("ROE(%)", 11.2, "center")]
    for label, x, ha in headers:
        ax.text(x, -0.5, label, fontsize=16, fontweight="bold",
                ha=ha, va="center", color=C_TEXT)

    cmap_score = plt.get_cmap("Blues")
    for r, (_, row) in enumerate(top.iterrows()):
        ax.text(0.0, r + 0.5, f"{r+1}", fontsize=16, ha="center", va="center")
        ax.text(1.0, r + 0.5, row["コード"], fontsize=16, ha="center", va="center")
        ax.text(2.5, r + 0.5, str(row["銘柄名"])[:14], fontsize=16, ha="left", va="center")

        # サプライズスコア（背景塗り）
        score = row["サプライズスコア"]
        color = cmap_score(np.clip(score / 100, 0.3, 0.9))
        rect = Rectangle((5.0 - 0.55, r + 0.05), 1.1, 0.9,
                         facecolor=color, edgecolor="white", linewidth=1.0)
        ax.add_patch(rect)
        txt_color = "white" if score > 60 else C_TEXT
        ax.text(5.0, r + 0.5, f"{score:.1f}", fontsize=16, fontweight="bold",
                ha="center", va="center", color=txt_color)

        # 個別指標
        ax.text(6.7, r + 0.5, f"{row['業績予想修正率(予)']:+.2f}",
                fontsize=16, ha="center", va="center", color=C_TEXT_SUB)
        ax.text(8.2, r + 0.5,
                f"{row['EPS予想超過率']:+.1f}" if pd.notna(row['EPS予想超過率']) else "—",
                fontsize=16, ha="center", va="center", color=C_TEXT_SUB)
        ax.text(9.9, r + 0.5,
                f"{row['経常利益変化率(予)']:+.2f}" if pd.notna(row['経常利益変化率(予)']) else "—",
                fontsize=16, ha="center", va="center", color=C_TEXT_SUB)
        ax.text(11.2, r + 0.5,
                f"{row['ROE']:.1f}" if pd.notna(row['ROE']) else "—",
                fontsize=16, ha="center", va="center", color=C_TEXT_SUB)

    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        f"サプライズスコア Top 20  ―  3 指標合成 × 時価総額 100 億円・ROE 5% 以上 (対象 {len(f):,} 銘柄)",
        fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left",
    )
    _savefig_vpad(fig, OUT_DIR / "01_surprise_top20.png")
    plt.close(fig)


# ── 2) 石油元売 3 社のサプライズ ─────────────────────────────────────────────
def make_oil_refining_surprise(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))

    labels = []
    revs = []
    epss = []
    ords_ = []
    rocols = []
    for code, label, color in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        labels.append(label)
        revs.append(r["業績予想修正率(予)"])
        epss.append(r["EPS予想超過率"] if pd.notna(r["EPS予想超過率"]) else 0)
        ords_.append(r["経常利益変化率(予)"] if pd.notna(r["経常利益変化率(予)"]) else 0)
        rocols.append(r["ROE"])

    n = len(labels)
    y = np.arange(n)
    h = 0.25

    ax.barh(y - h, revs, height=h, color=C_REV, alpha=0.85,
            edgecolor="white", linewidth=0.8, label="業績予想修正率(予)")
    ax.barh(y, epss, height=h, color=C_EPS, alpha=0.85,
            edgecolor="white", linewidth=0.8, label="EPS予想超過率")
    ax.barh(y + h, ords_, height=h, color=C_ORD, alpha=0.85,
            edgecolor="white", linewidth=0.8, label="経常利益変化率(予)")

    for i, (rv, ep, od) in enumerate(zip(revs, epss, ords_)):
        for v, y_off, c in [(rv, -h, C_REV), (ep, 0, C_EPS), (od, h, C_ORD)]:
            txt = f"{v:+.1f}%" if abs(v) > 0.01 else "—"
            ax.text(v + (1.0 if v >= 0 else -1.0), i + y_off, txt,
                    va="center", ha="left" if v >= 0 else "right",
                    fontsize=16, color=c, fontweight="bold")

    ax.axvline(0, color="#999999", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{lab}\n(ROE {ro:.1f}%)" for lab, ro in zip(labels, rocols)],
                       fontsize=16, color=C_TEXT)
    ax.invert_yaxis()
    ax.set_xlim(-15, 60)
    ax.set_xlabel("%", fontsize=16, color=C_TEXT_SUB)
    ax.legend(loc="lower right", fontsize=16, frameon=False)
    ax.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("石油元売 3 社  ―  3 シグナル比較（修正率 / EPS超過率 / 経常変化率(予)）",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    _savefig_vpad(fig, OUT_DIR / "02_oil_refining_surprise.png")
    plt.close(fig)


# ── 3) 修正率 × 経常変化率(予) 4 象限散布図 ─────────────────────────────────
def make_revision_vs_ordprofit(df: pd.DataFrame) -> None:
    f = df.copy()
    f = f[f["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]
    f = f.dropna(subset=["業績予想修正率(予)", "経常利益変化率(予)"])
    f = f[f["業績予想修正率(予)"].between(-30, 40) &
          f["経常利益変化率(予)"].between(-50, 100)]

    fig, ax = plt.subplots(figsize=(13, 7.5))

    # ── 4 象限を薄い背景色で塗り分け ────────────────────────────────
    ZONES = [
        (  0,   0,  40, 100, C_HOT,      0.08),  # 右上: 最強ゾーン
        (-30,   0,  30, 100, "#888888",  0.04),  # 左上: 下方修正×成長
        (-30, -50,  30,  50, "#888888",  0.04),  # 左下: 下方修正×減益
        (  0, -50,  40,  50, C_HOT,      0.05),  # 右下: 上方修正×減益（警戒）
    ]
    for x0, y0, w, h, color, alpha in ZONES:
        ax.add_patch(Rectangle((x0, y0), w, h,
                               facecolor=color, alpha=alpha,
                               edgecolor="none", zorder=0))

    # 背景銘柄
    cand = f[(f["業績予想修正率(予)"] >= 3) & (f["経常利益変化率(予)"] > 0)]
    bg = f.drop(cand.index, errors="ignore")
    ax.scatter(bg["業績予想修正率(予)"], bg["経常利益変化率(予)"],
               s=14, color=C_BG, alpha=0.30, edgecolors="none", zorder=1)

    # 注目銘柄
    ax.scatter(cand["業績予想修正率(予)"], cand["経常利益変化率(予)"],
               s=44, color=C_HOT, alpha=0.85, edgecolors="white", linewidth=0.6,
               zorder=4, label=f"上方修正 × 成長予想 ({len(cand)})")

    # 石油元売 3 社
    for code, label, _ in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        x, y = r["業績予想修正率(予)"], r["経常利益変化率(予)"]
        if pd.isna(y):
            continue
        ax.scatter(x, y, s=200, color=C_TEXT, edgecolor="white",
                   linewidth=2.0, zorder=8, marker="*")
        ax.annotate(label, xy=(x, y), xytext=(10, 8),
                    textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    bbox=dict(facecolor="white", alpha=0.92,
                              edgecolor="#aaaaaa", boxstyle="round,pad=0.3"),
                    zorder=9)

    # 基準線
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.axvline(0, color="#999999", linewidth=0.8)

    # ゾーンラベル
    ax.text(25, 50, "★最強ゾーン★\n上方修正 × 来期成長",
            fontsize=16, fontweight="bold", color=C_HOT, ha="center", va="center")
    ax.text(-20, 50, "下方修正 × 来期成長\n（回復期待・限定的）",
            fontsize=16, color=C_TEXT_SUB, ha="center", va="center")
    ax.text(-20, -25, "下方修正 × 来期減益\n（回避ゾーン）",
            fontsize=16, color=C_TEXT_SUB, ha="center", va="center")
    ax.text(25, -25, "上方修正 × 来期減益\n（ピークアウト警戒）",
            fontsize=16, color=C_TEXT_SUB, ha="center", va="center")

    ax.set_xlim(-30, 40)
    ax.set_ylim(-50, 100)
    ax.set_xlabel("業績予想修正率(予)（%）  ← 下方修正    上方修正 →",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("経常利益変化率(予)（%）  ← 来期減益    来期成長 →",
                  fontsize=16, color=C_TEXT)
    ax.set_title("リビジョン × 来期成長予想  ―  業績モメンタムの 4 象限",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper left", fontsize=16, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    _savefig_vpad(fig, OUT_DIR / "03_revision_vs_ordprofit.png")
    plt.close(fig)


# ── 4) 単一シグナル Top10 vs 合成スコア Top10 オーバーラップ ──────────────────
def make_signal_overlap(df: pd.DataFrame) -> None:
    """3 種類の単一シグナル Top10 と合成スコア Top10 の銘柄重なりを可視化。"""
    f = df.copy()
    f = f[f["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]
    f = f[f["業績予想修正率(予)"].notna() & (f["業績予想修正率(予)"] >= 0)]
    if f.empty:
        return

    top_rev = set(f.nlargest(10, "業績予想修正率(予)")["コード"])
    top_eps = set(f.nlargest(10, "EPS予想超過率")["コード"])
    top_ord = set(f.nlargest(10, "経常利益変化率(予)")["コード"])
    top_score = set(f.nlargest(10, "サプライズスコア")["コード"])

    # 合成スコア Top10 を縦に、3 単一シグナル Top10 への "in" を可視化
    sc10 = f.nlargest(10, "サプライズスコア").reset_index(drop=True)
    sc10.index += 1

    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(len(sc10) + 1, -1)

    # Header
    ax.text(0.2, -0.5, "順位", fontsize=16, fontweight="bold", ha="left", color=C_TEXT)
    ax.text(1.0, -0.5, "コード", fontsize=16, fontweight="bold", ha="center", color=C_TEXT)
    ax.text(2.5, -0.5, "銘柄名", fontsize=16, fontweight="bold", ha="left", color=C_TEXT)
    ax.text(5.0, -0.5, "合成SC", fontsize=16, fontweight="bold", ha="center", color=C_TEXT)
    ax.text(6.5, -0.5, "修正率\nTop10", fontsize=16, fontweight="bold", ha="center", color=C_REV)
    ax.text(7.7, -0.5, "EPS超過率\nTop10", fontsize=16, fontweight="bold", ha="center", color=C_EPS)
    ax.text(8.9, -0.5, "経常変化率\nTop10", fontsize=16, fontweight="bold", ha="center", color=C_ORD)
    ax.text(10.0, -0.5, "合致数", fontsize=16, fontweight="bold", ha="center", color=C_TEXT)

    for r, (_, row) in enumerate(sc10.iterrows()):
        code = row["コード"]
        in_rev = code in top_rev
        in_eps = code in top_eps
        in_ord = code in top_ord
        n_in = int(in_rev) + int(in_eps) + int(in_ord)

        ax.text(0.2, r + 0.5, f"{r+1}", fontsize=16, ha="left", va="center")
        ax.text(1.0, r + 0.5, code, fontsize=16, ha="center", va="center")
        ax.text(2.5, r + 0.5, str(row["銘柄名"])[:14], fontsize=16, ha="left", va="center")
        ax.text(5.0, r + 0.5, f"{row['サプライズスコア']:.1f}",
                fontsize=16, fontweight="bold", ha="center", va="center", color="#5a9a72")

        for x, in_set, c in [(6.5, in_rev, C_REV), (7.7, in_eps, C_EPS), (8.9, in_ord, C_ORD)]:
            if in_set:
                ax.scatter([x], [r + 0.5], s=180, color=c, alpha=0.85,
                           edgecolor="white", linewidth=1.5, zorder=3)
                ax.text(x, r + 0.5, "✓", fontsize=16, fontweight="bold",
                        ha="center", va="center", color="white")
            else:
                ax.text(x, r + 0.5, "—", fontsize=16, color="#cccccc",
                        ha="center", va="center")

        col_n = "#5a9a72" if n_in >= 2 else ("#F39C12" if n_in == 1 else "#cccccc")
        ax.text(10.0, r + 0.5, f"{n_in}/3", fontsize=16, fontweight="bold",
                ha="center", va="center", color=col_n)

    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.set_title("合成スコア Top10 と単一シグナル Top10 の重なり  ―  合成の効用",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")

    # 注釈
    n_all3 = sum(1 for _, row in sc10.iterrows()
                 if (row["コード"] in top_rev) and (row["コード"] in top_eps)
                 and (row["コード"] in top_ord))
    ax.text(0.0, len(sc10) + 0.7,
            f"合成 Top10 中、3 シグナル全部 Top10 入りは {n_all3} 銘柄。"
            f"単一指標で見落とされる銘柄を合成が拾う構造です。",
            fontsize=16, color=C_TEXT_SUB, va="top")

    _savefig_vpad(fig, OUT_DIR / "04_signal_overlap.png")
    plt.close(fig)


# ── 5) 3 シグナルの分布 ─────────────────────────────────────────────────────
def make_signal_distribution(df: pd.DataFrame) -> None:
    f = df.copy()
    f = f[f["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))

    configs = [
        (axes[0], f["業績予想修正率(予)"].dropna(), "業績予想修正率(予)", C_REV, (-30, 30)),
        (axes[1], f["EPS予想超過率"].dropna(),     "EPS予想超過率",     C_EPS, (-50, 150)),
        (axes[2], f["経常利益変化率(予)"].dropna(), "経常利益変化率(予)", C_ORD, (-50, 100)),
    ]

    for ax, s, title, color, xrange in configs:
        s = s[s.between(*xrange)]
        ax.hist(s, bins=40, color=color, alpha=0.7, edgecolor="white", linewidth=0.5)
        med = float(s.median())
        ax.axvline(med, color="#202124", linestyle="--", linewidth=1.0, alpha=0.6)
        ax.axvline(0, color="#aaaaaa", linewidth=0.7)
        ax.set_title(f"{title}  (中央 {med:+.1f}%)",
                     fontsize=16, fontweight="bold", color=C_TEXT)
        ax.set_xlim(*xrange)
        ax.tick_params(labelsize=16, colors=C_TEXT_SUB)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color=C_GRID, linewidth=0.5)

    fig.suptitle(f"3 シグナルの分布（時価総額 100 億円・ROE 5% 以上、{len(f):,} 銘柄）",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.02)
    plt.tight_layout()
    _savefig_vpad(fig, OUT_DIR / "05_signal_distribution.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_universe()
    df = add_surprise_score(df)
    print(f"[load] {len(df):,} 銘柄")

    make_surprise_top20(df)
    print("[ok] 01_surprise_top20.png")
    make_oil_refining_surprise(df)
    print("[ok] 02_oil_refining_surprise.png")
    make_revision_vs_ordprofit(df)
    print("[ok] 03_revision_vs_ordprofit.png")
    make_signal_overlap(df)
    print("[ok] 04_signal_overlap.png")
    make_signal_distribution(df)
    print("[ok] 05_signal_distribution.png")

    # 統計
    print("\n=== 統計 ===")
    f = df[(df["時価総額"].fillna(0) >= 10_000) & (df["ROE"].fillna(-99) >= 5)]
    f = f[f["業績予想修正率(予)"].notna() & (f["業績予想修正率(予)"] >= 0)]
    print(f"フィルタ後（修正率>=0 & ROE>=5 & MCap>=100億）: {len(f)}")
    print(f"サプライズスコア 75 以上: {(f['サプライズスコア'] >= 75).sum()}")
    print(f"サプライズスコア 90 以上: {(f['サプライズスコア'] >= 90).sum()}")

    print("\n=== 石油元売 3 社 ===")
    for c, n, _ in OIL_REFINERS:
        r = df.loc[df["コード"] == c]
        if r.empty: continue
        r = r.iloc[0]
        print(f"  {n}: 修正={r['業績予想修正率(予)']:+.2f}%  EPS超過={r['EPS予想超過率']:+.1f}%  経常変化(予)={r['経常利益変化率(予)']:+.2f}%  ROE={r['ROE']}%")
