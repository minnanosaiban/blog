"""
連載01: GARP スクリーナー ― PEG × ROE で「成長と割安の両立」を発掘（Streamlit + Plotly）

ローカル前提: C:\\stock_analysis 配下の rakunav CSV を読みに行く。
データは利用規約により再配布しないため、各自の環境でセットアップしてください。

起動: streamlit run app.py
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import streamlit as st
import plotly.express as px

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="GARP スクリーナー",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── データ取得 ──────────────────────────────────────────────
# rakunav 4 指標
RAKUNAV_SPECS = [
    (118, "ROE", "ROE(自己資本利益率)"),
    (113, "EPS実績", "EPS(一株あたり当期利益)"),
    (213, "EPS予想", "EPS(予)(一株あたり当期利益)"),
    (120, "時価総額", None),  # 列名は CSV ヘッダから自動判定
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


def _to_float_price(s):
    """現在値の "1,298.5" のような表記を float に。"""
    return _to_float(s)


@st.cache_data(ttl=3600, show_spinner="📥 楽天 MS2 CSV を読み込んでいます…")
def load_universe() -> pd.DataFrame:
    """rakunav 4 指標から PEG・ROE を計算した銘柄ユニバース。"""
    merged = None
    price_series = None
    for no, label, col_hint in RAKUNAV_SPECS:
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.strip()

        # 値カラム特定
        if col_hint:
            cand = [c for c in df.columns if c == col_hint or c.startswith(col_hint)]
        else:
            cand = [c for c in df.columns
                    if c not in ("コード", "銘柄名", "市場", "財務", "現在値", "前日比(%)")]
        df[label] = df[cand[0]].map(_to_float)

        # 現在値（最初に出会った CSV から取得）
        if price_series is None and "現在値" in df.columns:
            price_series = df.set_index("コード")["現在値"].map(_to_float_price)

        d = df[["コード", "銘柄名", "市場", label]]
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )

    merged["現在値"] = merged["コード"].map(price_series)
    merged["PER"] = merged["現在値"] / merged["EPS予想"].where(merged["EPS予想"] > 0)
    growth = ((merged["EPS予想"] - merged["EPS実績"]) / merged["EPS実績"].abs()) * 100
    growth = growth.where(merged["EPS実績"] > 0)
    merged["成長率%"] = growth
    merged["PEG"] = merged["PER"] / growth.where(growth > 0)

    merged = apply_master_names(merged)
    return merged


def classify_garp(df: pd.DataFrame, peg_th: float, roe_th: float) -> pd.Series:
    """PEG × ROE の 4 象限分類（左上=GARP理想）。"""
    zone = pd.Series("中立", index=df.index)
    cheap = df["PEG"] <= peg_th
    expensive = df["PEG"] > peg_th
    quality = df["ROE"] >= roe_th
    low_q = df["ROE"] < roe_th

    zone[cheap & quality]   = "🌟 GARP 理想ゾーン"
    zone[expensive & quality] = "💎 高品質 × 割高"
    zone[cheap & low_q]     = "⚠️ バリュートラップ警戒"
    zone[expensive & low_q] = "🚫 投資不適格"
    return zone


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# GARP<br>スクリーナー", unsafe_allow_html=True)

raw_codes = st.sidebar.text_area(
    "銘柄コード",
    value="5020\n5021\n5019",
    height=240,
    help="カンマ・改行・スペースで区切れます",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]

# しきい値（連載01 記事に合わせて固定）
PEG_TH = 1.0   # PEG ≤ 1.0 が割安
ROE_TH = 10.0  # ROE ≥ 10% が高品質


# ── データロード ──────────────────────────────────────────────
try:
    df_all = load_universe()
except Exception as e:
    st.error(f"データ読み込みに失敗: {e}")
    st.stop()

df_all = df_all.dropna(subset=["PEG", "ROE"]).copy()
df_all = df_all[df_all["PEG"] > 0]
df_all["分類"] = classify_garp(df_all, PEG_TH, ROE_TH)


# 入力コードでフィルタ
df = df_all[df_all["コード"].isin(tickers)].copy()
missing = [t for t in tickers if t not in df["コード"].values]


# ── メイン ──────────────────────────────────────────────
st.markdown("**⬛PEG × ROE GARP マップ**")
st.caption(f" PEG ≤ {PEG_TH:g} かつ ROE ≥ {ROE_TH:g}% が理想ゾーン")

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

if missing:
    st.warning(f"見つからなかった銘柄コード: {', '.join(missing)}")

if df.empty:
    st.error("有効な銘柄が見つかりませんでした（PEG・ROE が計算可能な銘柄のみ表示できます）")
    st.stop()


# ── 散布図 ──────────────────────────────────────────────
COLOR_MAP = {
    "🌟 GARP 理想ゾーン": "#27ae60",
    "💎 高品質 × 割高": "#3498db",
    "⚠️ バリュートラップ警戒": "#e67e22",
    "🚫 投資不適格": "#e74c3c",
    "中立": "#888888",
}

XLIM = (0.0, 3.0)
YLIM = (-10.0, 50.0)

# 表示範囲外は端に寄せて見えるようクリップ
df_plot = df.copy()
df_plot["PEG_表示"] = df_plot["PEG"].clip(lower=XLIM[0] + 0.01, upper=XLIM[1] - 0.01)
df_plot["ROE_表示"] = df_plot["ROE"].clip(lower=YLIM[0] + 0.5, upper=YLIM[1] - 0.5)
df_plot["ラベル"] = df_plot["銘柄名"] + " (" + df_plot["コード"] + ")"

fig = px.scatter(
    df_plot,
    x="PEG_表示",
    y="ROE_表示",
    color="分類",
    color_discrete_map=COLOR_MAP,
    text="ラベル",
    hover_data={
        "コード": True,
        "銘柄名": True,
        "PER": ":.1f",
        "成長率%": ":+.1f",
        "PEG": ":.2f",
        "ROE": ":.1f",
        "時価総額": ":,.0f",
        "現在値": ":,.0f",
        "PEG_表示": False,
        "ROE_表示": False,
        "分類": False,
        "ラベル": False,
    },
)
fig.update_traces(
    marker=dict(size=14, line=dict(width=1.5, color="white")),
    textposition="top center",
    textfont=dict(size=12, color="#202124"),
)
fig.update_xaxes(
    title="PEG（予想） ← 割安　割高 →",
    range=list(XLIM),
    tickvals=[0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)
fig.update_yaxes(
    title="ROE（%） ← 低収益　高収益 →",
    range=list(YLIM),
    tickvals=[-10, 0, 10, 20, 30, 40, 50],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)

# 4 象限を薄い背景色で識別（左上=GARP理想）
ZONE_FILL = [
    # (x0, x1, y0, y1, fillcolor)
    (XLIM[0], PEG_TH,  ROE_TH, YLIM[1], "rgba(39, 174, 96, 0.10)"),   # 左上: GARP理想
    (PEG_TH,  XLIM[1], ROE_TH, YLIM[1], "rgba(52, 152, 219, 0.08)"),  # 右上: 高品質 × 割高
    (XLIM[0], PEG_TH,  YLIM[0], ROE_TH, "rgba(230, 126, 34, 0.08)"),  # 左下: バリュートラップ警戒
    (PEG_TH,  XLIM[1], YLIM[0], ROE_TH, "rgba(231, 76, 60, 0.08)"),   # 右下: 投資不適格
]
for x0, x1, y0, y1, color in ZONE_FILL:
    fig.add_shape(
        type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
        fillcolor=color, line=dict(width=0), layer="below",
    )
fig.add_vline(x=PEG_TH, line_dash="dash", line_color="rgba(0,0,0,0.3)")
fig.add_hline(y=ROE_TH, line_dash="dash", line_color="rgba(0,0,0,0.3)")

fig.update_layout(
    height=600,
    legend=dict(
        orientation="v",
        yanchor="top", y=0.98,
        xanchor="left", x=0.01,
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="rgba(0,0,0,0.1)",
        borderwidth=1,
    ),
    margin=dict(t=20, b=40, l=40, r=20),
)

st.plotly_chart(fig, use_container_width=True)


# ── 詳細テーブル ──────────────────────────────────────────────
st.markdown("**⬛銘柄一覧**")
detail = df[[
    "コード", "銘柄名", "現在値", "PER", "成長率%", "PEG", "ROE", "時価総額", "分類",
]].copy()
st.dataframe(
    detail.style.format({
        "現在値": "{:,.0f}",
        "PER": "{:.1f}倍",
        "成長率%": "{:+.1f}%",
        "PEG": "{:.2f}",
        "ROE": "{:.1f}%",
        "時価総額": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)
