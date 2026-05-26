"""
連載05: 信用需給ダッシュボード ― 業績 × 需給 4 象限マトリクス（Streamlit + Plotly）

ローカル前提: C:\\stock_analysis 配下の rakunav CSV を読みに行く。
Streamlit Cloud デプロイ時は data/ にスナップショット CSV を同梱する形に切替予定。

起動: streamlit run app.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="信用需給ダッシュボード",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── データ取得 ──────────────────────────────────────────────
RAKUNAV_SPECS = [
    (311, "信用残(買)"),
    (312, "信用残(売)"),
    (313, "前週比(買)"),
    (314, "前週比(売)"),
    (138, "信用残/売買高レシオ"),
    (220, "業績予想修正率(予)"),
    (118, "ROE"),
    (120, "時価総額"),
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


@st.cache_data(ttl=3600, show_spinner="📥 楽天 MS2 CSV を読み込んでいます…")
def load_universe() -> pd.DataFrame:
    """rakunav 8 指標 + yfinance 価格メトリクスを merge した銘柄ユニバース。"""
    merged = None
    for no, col in RAKUNAV_SPECS:
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.strip()
        cand = [c for c in df.columns if c == col or c.startswith(col)]
        df[col] = df[cand[0]].map(_to_float)
        d = df[["コード", "銘柄名", "市場", col]]
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )

    merged["信用倍率"] = merged["信用残(買)"] / merged["信用残(売)"].where(merged["信用残(売)"] > 0)
    merged = apply_master_names(merged)
    return merged


def classify_fund_vs_credit(df: pd.DataFrame, rev_th: float, cr_hot: float, cr_short: float) -> pd.Series:
    """業績軸（修正率）× 需給軸（信用倍率）の 4 象限分類。"""
    zone = pd.Series("中立", index=df.index)
    ok = df["業績予想修正率(予)"] >= rev_th
    ng = df["業績予想修正率(予)"] <= -rev_th
    hot = df["信用倍率"] > cr_hot
    short = df["信用倍率"] <= cr_short

    zone[ok & hot] = "🟢 業績OK × 踏み上げ候補"
    zone[ok & short] = "🔵 業績OK × 空売り優位"
    zone[ng & hot] = "🔴 業績NG × 踏み上げ罠"
    zone[ng & short] = "🟠 業績NG × 空売り正解"
    return zone


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# 信用需給<br>ダッシュボード", unsafe_allow_html=True)

# 1) 銘柄コード入力（最上部・大きめ）
raw_codes = st.sidebar.text_area(
    "銘柄コード",
    value="5020\n5021\n5019",
    height=240,
    help="カンマ・改行・スペースで区切れます",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]

# 4 象限のしきい値（連載05 で定義した値で固定）
rev_th = 3.0     # 業績予想修正率 ±3%
cr_hot = 5.0     # 踏み上げ寄り 信用倍率 > 5 倍
cr_short = 1.0   # 空売り優位   信用倍率 ≤ 1 倍


# ── データロード ──────────────────────────────────────────────
try:
    df_all = load_universe()
except Exception as e:
    st.error(f"データ読み込みに失敗: {e}")
    st.stop()

df_all = df_all.dropna(subset=["業績予想修正率(予)", "信用倍率"]).copy()
df_all["分類"] = classify_fund_vs_credit(df_all, rev_th, cr_hot, cr_short)


# 入力コードでフィルタ
df = df_all[df_all["コード"].isin(tickers)].copy()
missing = [t for t in tickers if t not in df["コード"].values]


# ── メイン ──────────────────────────────────────────────

st.markdown("**⬛業績軸 × 需給軸**")
st.caption(" 業績予想修正率と信用倍率の 4 象限マトリクス")

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

if missing:
    st.warning(f"見つからなかった銘柄コード: {', '.join(missing)}")

if df.empty:
    st.error("有効な銘柄が見つかりませんでした")
    st.stop()


# ── 散布図 ──────────────────────────────────────────────
COLOR_MAP = {
    "🟢 業績OK × 踏み上げ候補": "#27ae60",
    "🔴 業績NG × 踏み上げ罠": "#e74c3c",
    "🔵 業績OK × 空売り優位": "#3498db",
    "🟠 業績NG × 空売り正解": "#e67e22",
    "中立": "#888888",
}

df_plot = df.copy()
df_plot["信用倍率_表示"] = df_plot["信用倍率"].clip(upper=200)
df_plot["ラベル"] = df_plot["銘柄名"] + " (" + df_plot["コード"] + ")"

fig = px.scatter(
    df_plot,
    x="業績予想修正率(予)",
    y="信用倍率_表示",
    color="分類",
    color_discrete_map=COLOR_MAP,
    text="ラベル",
    hover_data={
        "コード": True,
        "銘柄名": True,
        "信用残(買)": ":,.0f",
        "前週比(買)": ":+,.0f",
        "ROE": ":.1f",
        "時価総額": ":,.0f",
        "業績予想修正率(予)": ":.2f",
        "信用倍率_表示": False,
        "信用倍率": ":.2f",
        "分類": False,
        "ラベル": False,
    },
)
fig.update_traces(
    marker=dict(size=14, line=dict(width=1.5, color="white")),
    textposition="top center",
    textfont=dict(size=12, color="#202124"),
)
import math
y_ticks = [0.1, 0.5, 1, 2, 5, 10, 20, 50, 100]
fig.update_yaxes(
    type="log", title="信用倍率（対数） ← 空売り優位　踏み上げ →",
    range=[-1, 2],
    tickvals=y_ticks,
    ticktext=[f"{v:g}倍" for v in y_ticks],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)
fig.update_xaxes(
    title="業績予想修正率(%) ← 下振れ　上振れ →",
    range=[-30, 30],
    tickvals=[-30, -20, -10, -3, 0, 3, 10, 20, 30],
    ticktext=["-30", "-20", "-10", "-3", "0", "+3", "+10", "+20", "+30"],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)

# 4 象限を薄い背景色で識別
ZONE_FILL = [
    # (x0, x1, y0, y1, fillcolor)
    (-30, -rev_th, cr_hot, 100,    "rgba(231, 76, 60, 0.08)"),   # 踏み上げ罠
    (rev_th,  30,  cr_hot, 100,    "rgba(39, 174, 96, 0.10)"),   # 踏み上げ候補
    (-30, -rev_th, 0.1, cr_short,  "rgba(230, 126, 34, 0.08)"),  # 空売り正解
    (rev_th,  30,  0.1, cr_short,  "rgba(52, 152, 219, 0.08)"),  # 空売り優位
]
for x0, x1, y0, y1, color in ZONE_FILL:
    fig.add_shape(
        type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
        fillcolor=color, line=dict(width=0), layer="below",
    )

fig.update_layout(
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=20, b=40, l=40, r=20),
)

st.plotly_chart(fig, use_container_width=True)


# ── 詳細テーブル ──────────────────────────────────────────────
st.markdown("**⬛銘柄一覧**")
detail = df[[
    "コード", "銘柄名", "業績予想修正率(予)", "信用倍率",
    "信用残(買)", "信用残(売)", "前週比(買)", "ROE", "時価総額", "分類",
]].copy()
st.dataframe(
    detail.style.format({
        "業績予想修正率(予)": "{:+.2f}%",
        "信用倍率": "{:.2f}倍",
        "信用残(買)": "{:,.0f}",
        "信用残(売)": "{:,.0f}",
        "前週比(買)": "{:+,.0f}",
        "ROE": "{:.1f}%",
        "時価総額": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)
