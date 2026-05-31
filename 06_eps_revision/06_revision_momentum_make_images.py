"""
blog/03_EPSリビジョンモメンタム.md 用の画像生成スクリプト。

生成画像:
  01_market_revision.png       — 市場別 上方/下方修正銘柄数 + 修正比率
  02_oil_refining_revision.png — 石油元売 3 社のリビジョン × モメンタム
  03_revision_strength.png     — 大幅上方/下方修正 Top10 横棒
  04_revision_vs_momentum.png  — 4 象限散布図（出遅れ買い + 逆行注意）
  05_revision_vs_valuation.png — 4 象限散布図（修正済み割安）

実行: python scripts/blog/06_eps_revision_momentum_make_images.py
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
from utils.price_metrics import compute_price_metrics
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

C_UP    = "#5a9a72"  # 緑: 上方修正
C_DOWN  = "#c87878"  # 赤: 下方修正
C_WARN  = "#F39C12"  # オレンジ: 逆行注意
C_VAL   = "#3498db"  # 青: 修正済み割安
C_BG    = "#cccccc"
C_TEXT  = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID  = "#eaeaea"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/06_eps_revision_momentum")
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
    (220, "業績予想修正率(予)",         "業績予想修正率(予)"),
    (213, "EPS(予)(一株あたり当期利益)", "EPS予"),
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
    merged["PER予"] = merged["Close_yf"] / merged["EPS予"].where(merged["EPS予"] > 0)

    pm = compute_price_metrics(merged["コード"].tolist())
    merged = merged.merge(pm, on="コード", how="left")
    merged = apply_master_names(merged)
    return merged


OIL_REFINERS = [
    ("5021", "コスモエネＨＤ", "#888888"),
    ("5020", "ＥＮＥＯＳ",      "#444444"),
    ("5019", "出光興産",       "#aaaaaa"),
]


# ── 1) 市場別リビジョン地合い ───────────────────────────────────────────────
def make_market_revision(df: pd.DataFrame) -> None:
    target_markets = ["東P", "東S", "東G"]
    stats = []
    for mk in target_markets:
        s = df[df["市場"] == mk]["業績予想修正率(予)"].dropna()
        s = s[s != 0]
        u = (s > 0).sum()
        d = (s < 0).sum()
        stats.append({"市場": mk, "上方修正": u, "下方修正": d,
                      "比率": u / d if d > 0 else np.nan})
    sdf = pd.DataFrame(stats)

    # 全体
    s_all = df["業績予想修正率(予)"].dropna()
    s_all = s_all[s_all != 0]
    total_u = (s_all > 0).sum()
    total_d = (s_all < 0).sum()
    total_ratio = total_u / total_d

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(12.5, 4.6),
                                     gridspec_kw=dict(width_ratios=[1.4, 1]))

    # 左: 市場別グルーピング棒
    x = np.arange(len(sdf))
    w = 0.36
    ax_l.bar(x - w/2, sdf["上方修正"], width=w, color=C_UP, label="上方修正")
    ax_l.bar(x + w/2, sdf["下方修正"], width=w, color=C_DOWN, label="下方修正")
    for i, row in sdf.iterrows():
        ax_l.text(i - w/2, row["上方修正"] + 4, f"{int(row['上方修正'])}",
                  ha="center", va="bottom", fontsize=16, color=C_UP, fontweight="bold")
        ax_l.text(i + w/2, row["下方修正"] + 4, f"{int(row['下方修正'])}",
                  ha="center", va="bottom", fontsize=16, color=C_DOWN, fontweight="bold")
    ax_l.set_xticks(x)
    ax_l.set_xticklabels(sdf["市場"], fontsize=16, color=C_TEXT)
    ax_l.set_title("市場別 上方/下方修正 銘柄数",
                   fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax_l.legend(loc="upper right", fontsize=16, frameon=False)
    ax_l.grid(axis="y", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_ylim(0, max(sdf["上方修正"].max(), sdf["下方修正"].max()) * 1.18)

    # 右: 修正比率テーブル風 + 全体
    ax_r.axis("off")
    ax_r.set_xlim(0, 1)
    ax_r.set_ylim(0, 1)
    ax_r.text(0.0, 0.95, "修正比率（上方 ÷ 下方）", fontsize=16,
              fontweight="bold", color=C_TEXT, va="top")

    rows = [("全市場", total_u, total_d, total_ratio)] + [
        (r["市場"], int(r["上方修正"]), int(r["下方修正"]), r["比率"])
        for _, r in sdf.iterrows()
    ]
    y0 = 0.78
    for i, (mk, u, d, ratio) in enumerate(rows):
        y = y0 - i * 0.16
        color = C_UP if ratio >= 1.5 else (C_DOWN if ratio < 0.8 else "#888888")
        label = "強気" if ratio >= 1.5 else "中立" if ratio >= 0.8 else "弱気"
        ax_r.text(0.0, y, mk, fontsize=16, fontweight="bold", color=C_TEXT)
        ax_r.text(0.32, y, f"{u}/{d}", fontsize=16, color=C_TEXT_SUB)
        ax_r.text(0.62, y, f"{ratio:.2f}", fontsize=16, fontweight="bold", color=color)
        ax_r.text(0.84, y, label, fontsize=16, color=color)

    ax_r.text(0.0, 0.02,
              "判定: ≥1.5 強気 / 0.8〜1.5 中立 / <0.8 弱気",
              fontsize=16, color=C_TEXT_SUB, va="bottom")

    fig.suptitle(f"市場全体のリビジョン地合い  ―  対象 {len(df):,} 銘柄",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.02)
    _savefig_vpad(fig, OUT_DIR / "01_market_revision.png")
    plt.close(fig)


# ── 2) 石油元売 3 社のリビジョン ───────────────────────────────────────────
def make_oil_refining_revision(df: pd.DataFrame) -> None:
    """3 社の修正率と値上り率を左右 2 パネルで比較。各パネルで軸スケールを独立させる。"""
    labels, rev_vals, rise_vals, per_vals = [], [], [], []
    for code, label, _color in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        labels.append(label)
        rev_vals.append(r["業績予想修正率(予)"])
        rise_vals.append(r["値上り率"])
        per_vals.append(r["PER予"])

    code_to_color = {code: c for code, _, c in OIL_REFINERS}
    dot_colors = []
    for code, _, _ in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if not r.empty:
            dot_colors.append(code_to_color[code])

    n = len(labels)
    y = np.arange(n)
    h = 0.4
    y_labels = [f"{lab}\n(PER予想 {p:.1f})" for lab, p in zip(labels, per_vals)]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13, 5),
                                      gridspec_kw=dict(wspace=0.08))

    def _draw_panel(ax, vals, title, show_yticks):
        ax.barh(y, vals, height=h, color="#cccccc", alpha=1.0,
                edgecolor="white", linewidth=0.8)
        ax.axvline(0, color="#999999", linewidth=0.8)
        for i, v in enumerate(vals):
            offset = abs(max(vals, key=abs)) * 0.06 if vals else 0.1
            ax.text(v + (offset if v >= 0 else -offset), i,
                    f"{v:+.2f}%", va="center",
                    ha="left" if v >= 0 else "right",
                    fontsize=16, fontweight="bold", color=C_TEXT)
        ax.set_yticks(y)
        if show_yticks:
            ax.set_yticklabels([""] * n)
            for i, (label, dc) in enumerate(zip(y_labels, dot_colors)):
                ax.text(-0.02, i, "●", transform=ax.get_yaxis_transform(),
                        ha="right", va="center", fontsize=14, color=dc)
                ax.text(-0.06, i, label, transform=ax.get_yaxis_transform(),
                        ha="right", va="center", fontsize=14, color=C_TEXT)
        else:
            ax.set_yticklabels([""] * n)
        ax.invert_yaxis()
        pad = max(abs(v) for v in vals) * 0.35 if vals else 0.5
        ax.set_xlim(-(max(abs(v) for v in vals) + pad),
                     (max(abs(v) for v in vals) + pad))
        ax.set_title(title, fontsize=16, fontweight="bold",
                     color=C_TEXT, pad=24, loc="left")
        ax.set_xlabel("%", fontsize=16, color=C_TEXT_SUB)
        ax.grid(axis="x", color=C_GRID, linewidth=0.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

    _draw_panel(ax_l, rev_vals, "業績予想修正率(予)", show_yticks=True)
    _draw_panel(ax_r, rise_vals, "値上り率（日次%）",  show_yticks=False)

    fig.suptitle("石油元売 3 社  ―  業績予想修正率 vs 値上り率",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.02)
    _savefig_vpad(fig, OUT_DIR / "02_oil_refining_revision.png")
    plt.close(fig)


# ── 3) リビジョン強度ランキング ────────────────────────────────────────────
def make_revision_strength(df: pd.DataFrame) -> None:
    """大幅上方/下方修正 Top10 を横棒で並べる。極端な異常値（-90%等）も注釈"""
    f = df.copy()
    # 流動性フィルタ
    f = f[f["時価総額"].fillna(0) >= 10_000]

    top_up = f[f["業績予想修正率(予)"] > 0].nlargest(10, "業績予想修正率(予)").iloc[::-1]
    top_dn = f[f["業績予想修正率(予)"] < 0].nsmallest(10, "業績予想修正率(予)").iloc[::-1]

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13, 6),
                                     gridspec_kw=dict(wspace=0.45))

    # 上方
    y = np.arange(len(top_up))
    ax_l.barh(y, top_up["業績予想修正率(予)"], color=C_UP, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, (_, r) in enumerate(top_up.iterrows()):
        ax_l.text(r["業績予想修正率(予)"] + 0.4, i,
                  f"+{r['業績予想修正率(予)']:.1f}%",
                  va="center", fontsize=16, color=C_UP, fontweight="bold")
    ax_l.set_yticks(y)
    ax_l.set_yticklabels([f"{r['コード']} {r['銘柄名']}"
                          for _, r in top_up.iterrows()],
                         fontsize=16, color=C_TEXT)
    ax_l.set_xlabel("業績予想修正率(予)（%）", fontsize=16, color=C_TEXT_SUB)
    ax_l.set_xlim(0, top_up["業績予想修正率(予)"].max() * 1.15)
    ax_l.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_l.spines[sp].set_visible(False)
    ax_l.set_title("大幅上方修正 Top10", fontsize=16, fontweight="bold",
                   color=C_TEXT, pad=24, loc="left")

    # 下方
    y = np.arange(len(top_dn))
    ax_r.barh(y, top_dn["業績予想修正率(予)"], color=C_DOWN, alpha=0.85,
              edgecolor="white", linewidth=0.8)
    for i, (_, r) in enumerate(top_dn.iterrows()):
        ax_r.text(r["業績予想修正率(予)"] - 0.4, i,
                  f"{r['業績予想修正率(予)']:.1f}%",
                  va="center", ha="right",
                  fontsize=16, color=C_DOWN, fontweight="bold")
    ax_r.set_yticks(y)
    ax_r.set_yticklabels([f"{r['コード']} {r['銘柄名']}"
                          for _, r in top_dn.iterrows()],
                         fontsize=16, color=C_TEXT)
    ax_r.set_xlabel("業績予想修正率(予想)（%）", fontsize=16, color=C_TEXT_SUB)
    ax_r.set_xlim(top_dn["業績予想修正率(予)"].min() * 1.15, 0)
    ax_r.grid(axis="x", color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax_r.spines[sp].set_visible(False)
    ax_r.set_title("大幅下方修正 Top10", fontsize=16, fontweight="bold",
                   color=C_TEXT, pad=24, loc="left")

    fig.suptitle("リビジョン強度ランキング  ―  時価総額 100 億円以上",
                 fontsize=16, fontweight="bold", color=C_TEXT, y=1.00)
    _savefig_vpad(fig, OUT_DIR / "03_revision_strength.png")
    plt.close(fig)


# ── 4) リビジョン × モメンタム 散布図 ────────────────────────────────────────
def make_revision_vs_momentum(df: pd.DataFrame) -> None:
    f = df.copy()
    f = f[f["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]
    f = f.dropna(subset=["業績予想修正率(予)", "値上り率"])
    f = f[f["業績予想修正率(予)"].between(-30, 30) & f["値上り率"].between(-15, 15)]

    fig, ax = plt.subplots(figsize=(13, 7.5))

    # ── 4 象限を薄い背景色で塗り分け ────────────────────────────────
    # (x0, y0, width, height, facecolor)
    ZONES = [
        (  0, -15,  30, 17, C_UP,       0.08),  # 右下: 出遅れ買い候補
        (-30,   2,  30, 13, C_WARN,     0.07),  # 左上: 逆行注意
        (  0,   2,  30, 13, "#888888",  0.04),  # 右上: 既反応
        (-30, -15,  30, 17, "#888888",  0.04),  # 左下: 底入れ待ち
    ]
    for x0, y0, w, h, color, alpha in ZONES:
        ax.add_patch(Rectangle((x0, y0), w, h,
                               facecolor=color, alpha=alpha,
                               edgecolor="none", zorder=0))

    # 背景銘柄
    bg = f[~((f["業績予想修正率(予)"] >= 3) & (f["値上り率"] <= 2))]
    bg = bg[~((bg["業績予想修正率(予)"] <= -3) & (bg["値上り率"] >= 2))]
    ax.scatter(bg["業績予想修正率(予)"], bg["値上り率"],
               s=14, color=C_BG, alpha=0.30, edgecolors="none", zorder=1)

    # 出遅れ買い候補
    lag = f[(f["業績予想修正率(予)"] >= 3) & (f["値上り率"] <= 2)]
    ax.scatter(lag["業績予想修正率(予)"], lag["値上り率"],
               s=44, color=C_DOWN, alpha=0.75, edgecolors="white", linewidth=0.6,
               zorder=4, label=f"出遅れ買い候補 ({len(lag)})")

    # 逆行注意
    warn = f[(f["業績予想修正率(予)"] <= -3) & (f["値上り率"] >= 2)]
    ax.scatter(warn["業績予想修正率(予)"], warn["値上り率"],
               s=44, color=C_WARN, alpha=0.85, edgecolors="white", linewidth=0.6,
               zorder=4, label=f"逆行注意 ({len(warn)})")

    # 石油元売 3 社ハイライト（重なり回避のため社ごとにオフセットを設定）
    _offsets = {"5021": (10, 12), "5020": (-10, 18), "5019": (10, -22)}
    for code, label, _ in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        x, y = r["業績予想修正率(予)"], r["値上り率"]
        ox, oy = _offsets.get(code, (10, 8))
        ax.scatter(x, y, s=180, color=C_TEXT, edgecolor="white",
                   linewidth=2.0, zorder=8, marker="*")
        ax.annotate(label, xy=(x, y), xytext=(ox, oy),
                    textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    bbox=dict(facecolor="white", alpha=0.92,
                              edgecolor="#aaaaaa", boxstyle="round,pad=0.3"),
                    zorder=9)

    # 基準線
    ax.axhline(0, color="#777777", linewidth=0.8)
    ax.axvline(0, color="#777777", linewidth=0.8)

    # ゾーンラベル
    ax.text(20, -10, "★出遅れ買い候補★\n上方修正 × 株価未反応",
            fontsize=16, fontweight="bold", color=C_DOWN, ha="center", va="center")
    ax.text(-20, 10, "逆行注意\n下方修正 × 株価上昇",
            fontsize=16, color=C_WARN, ha="center", va="center")
    ax.text(20, 10, "既反応 / 利食い検討", fontsize=16, color=C_TEXT_SUB,
            ha="center", va="center")
    ax.text(-20, -10, "底入れ待ち\n下方修正 × 株価下落", fontsize=16,
            color=C_TEXT_SUB, ha="center", va="center")

    ax.set_xlim(-30, 30)
    ax.set_ylim(-15, 15)
    ax.set_xlabel("業績予想修正率(予)（%）  ← 下方修正    上方修正 →",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("値上り率（%）  ← 株価下落    株価上昇 →",
                  fontsize=16, color=C_TEXT)
    ax.set_title("リビジョン × 株価モメンタム  ―  4 象限の戦略マップ",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.99),
              ncol=2, fontsize=14, frameon=True,
              facecolor="white", edgecolor="#dddddd", framealpha=0.9)
    _savefig_vpad(fig, OUT_DIR / "04_revision_vs_momentum.png")
    plt.close(fig)


# ── 5) リビジョン × バリュエーション 散布図 ──────────────────────────────────
def make_revision_vs_valuation(df: pd.DataFrame) -> None:
    f = df.copy()
    f = f[f["時価総額"].fillna(0) >= 10_000]
    f = f[f["ROE"].fillna(-99) >= 5]
    f = f.dropna(subset=["業績予想修正率(予)", "PER予"])
    f = f[f["業績予想修正率(予)"].between(-30, 30) & f["PER予"].between(0, 40)]

    fig, ax = plt.subplots(figsize=(13, 7.5))

    # ゾーン背景
    ax.axhspan(0, 15, xmin=(3 - (-30)) / 60, xmax=1.0,
               facecolor=C_VAL, alpha=0.07)  # 修正済み割安

    # 背景銘柄
    cand = f[(f["業績予想修正率(予)"] >= 3) & (f["PER予"] <= 15)]
    bg = f.drop(cand.index, errors="ignore")
    ax.scatter(bg["業績予想修正率(予)"], bg["PER予"],
               s=14, color=C_BG, alpha=0.30, edgecolors="none", zorder=1)

    # 修正済み割安候補
    ax.scatter(cand["業績予想修正率(予)"], cand["PER予"],
               s=46, color=C_VAL, alpha=0.85, edgecolors="white", linewidth=0.6,
               zorder=4, label=f"修正済み割安候補 ({len(cand)})")

    # 石油元売 3 社ハイライト
    for code, label, _ in OIL_REFINERS:
        r = df.loc[df["コード"] == code]
        if r.empty:
            continue
        r = r.iloc[0]
        if pd.isna(r["PER予"]):
            continue
        x, y = r["業績予想修正率(予)"], r["PER予"]
        ax.scatter(x, y, s=180, color=C_TEXT, edgecolor="white",
                   linewidth=2.0, zorder=8, marker="*")
        ax.annotate(label, xy=(x, y), xytext=(10, -10),
                    textcoords="offset points",
                    fontsize=16, fontweight="bold", color=C_TEXT,
                    bbox=dict(facecolor="white", alpha=0.92,
                              edgecolor="#aaaaaa", boxstyle="round,pad=0.3"),
                    zorder=9)

    # 基準線
    ax.axvline(3, color=C_VAL, linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axhline(15, color=C_VAL, linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(0, color="#999999", linewidth=0.8)

    ax.text(20, 7, "★修正済み割安★\n上方修正 × 低PER",
            fontsize=16, fontweight="bold", color=C_VAL, ha="center", va="center")
    ax.text(-20, 25, "下方修正 × 割高", fontsize=16, color=C_TEXT_SUB,
            ha="center", va="center")
    ax.text(20, 25, "上方修正だが割高グロース", fontsize=16, color=C_TEXT_SUB,
            ha="center", va="center")

    ax.set_xlim(-30, 30)
    ax.set_ylim(0, 40)
    ax.set_xlabel("業績予想修正率(予)（%）  ← 下方修正    上方修正 →",
                  fontsize=16, color=C_TEXT)
    ax.set_ylabel("PER（予）  ← 割安    割高 →", fontsize=16, color=C_TEXT)
    ax.set_title("リビジョン × バリュエーション  ―  修正済み割安銘柄の発掘",
                 fontsize=16, fontweight="bold", color=C_TEXT, pad=24, loc="left")
    ax.grid(color=C_GRID, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper right", fontsize=16, frameon=True,
              facecolor="white", edgecolor="#dddddd")
    _savefig_vpad(fig, OUT_DIR / "05_revision_vs_valuation.png")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_universe()
    print(f"[load] {len(df):,} 銘柄")

    make_market_revision(df)
    print("[ok] 01_market_revision.png")
    make_oil_refining_revision(df)
    print("[ok] 02_oil_refining_revision.png")
    make_revision_strength(df)
    print("[ok] 03_revision_strength.png")
    make_revision_vs_momentum(df)
    print("[ok] 04_revision_vs_momentum.png")
    make_revision_vs_valuation(df)
    print("[ok] 05_revision_vs_valuation.png")

    # 統計値
    s = df["業績予想修正率(予)"].dropna()
    s = s[s != 0]
    print(f"\n=== 統計 ===")
    print(f"上方修正: {(s>0).sum()} 銘柄")
    print(f"下方修正: {(s<0).sum()} 銘柄")
    print(f"修正比率: {(s>0).sum() / (s<0).sum():.2f}")

    f = df[(df["時価総額"].fillna(0) >= 10_000) & (df["ROE"].fillna(-99) >= 5)]
    lag = f[(f["業績予想修正率(予)"] >= 3) & (f["値上り率"] <= 2)]
    warn = f[(f["業績予想修正率(予)"] <= -3) & (f["値上り率"] >= 2)]
    val = f[(f["業績予想修正率(予)"] >= 3) & (f["PER予"].between(0, 15))]
    print(f"\nフィルタ後: {len(f)} 銘柄")
    print(f"出遅れ買い候補（修正>=3 & 値上り<=2）: {len(lag)}")
    print(f"逆行注意（修正<=-3 & 値上り>=2）: {len(warn)}")
    print(f"修正済み割安（修正>=3 & PER<=15）: {len(val)}")
