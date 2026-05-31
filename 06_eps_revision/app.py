"""
連載03: EPSリビジョン・モメンタム ― 業績予想修正率 × 値上り率 4 象限マトリクス（Streamlit + Plotly）

ローカル前提: C:\\stock_analysis 配下の rakunav CSV を読みに行く。
データは利用規約により再配布しないため、各自の環境でセットアップしてください。

起動: streamlit run app.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import streamlit as st
import plotly.express as px

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="EPSリビジョン・モメンタム",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── データ取得 ──────────────────────────────────────────────
RAKUNAV_SPECS = [
    (220, "業績予想修正率(予)", "業績予想修正率(予)"),
    (213, "EPS予", "EPS(予)(一株あたり当期利益)"),
    (118, "ROE", "ROE(自己資本利益率)"),
    (120, "時価総額", None),
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


@st.cache_data(ttl=3600, show_spinner="📈 yfinance から株価を取得中…")
def fetch_price_metrics(tickers: tuple[str, ...]) -> pd.DataFrame:
    """各銘柄の 現在値・値上り率（直近5営業日累計%）を yfinance から取得。"""
    import yfinance as yf
    rows = []
    for code in tickers:
        try:
            hist = yf.Ticker(f"{code}.T").history(period="15d", auto_adjust=True)
            close = hist["Close"].dropna()
            if len(close) < 6:
                continue
            latest = float(close.iloc[-1])
            ref = float(close.iloc[-6])  # 5 営業日前
            chg = (latest / ref - 1) * 100 if ref > 0 else None
            rows.append({"コード": code, "現在値": latest, "値上り率": chg})
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner="📥 楽天 MS2 CSV を読み込んでいます…")
def load_universe() -> pd.DataFrame:
    """rakunav 4 指標を merge した銘柄ユニバース。"""
    merged = None
    for no, label, col_hint in RAKUNAV_SPECS:
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.strip()
        if col_hint:
            cand = [c for c in df.columns if c == col_hint or c.startswith(col_hint)]
        else:
            cand = [c for c in df.columns
                    if c not in ("コード", "銘柄名", "市場", "財務", "現在値", "前日比(%)")]
        df[label] = df[cand[0]].map(_to_float)
        d = df[["コード", "銘柄名", "市場", label]]
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )
    merged = apply_master_names(merged)
    return merged


def classify_revision(df: pd.DataFrame, rev_th: float, rise_th: float) -> pd.Series:
    """業績予想修正率 × 値上り率 の 4 象限分類（右下=出遅れ買い候補）。"""
    zone = pd.Series("中立", index=df.index)
    up_rev = df["業績予想修正率(予)"] >= rev_th
    dn_rev = df["業績予想修正率(予)"] <= -rev_th
    up_rise = df["値上り率"] >= rise_th
    dn_rise = df["値上り率"] <= -rise_th

    zone[up_rev & dn_rise] = "🎯 出遅れ買い候補"
    zone[dn_rev & up_rise] = "🚨 逆行注意"
    zone[up_rev & up_rise] = "💨 既に反応済み"
    zone[dn_rev & dn_rise] = "⏳ 底入れ待ち"
    return zone


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# EPSリビジョン<br>モメンタム", unsafe_allow_html=True)
today_obj = datetime.now()
today_str = f"{today_obj.year}年{today_obj.month}月{today_obj.day}日"
st.sidebar.caption(today_str)

raw_codes = st.sidebar.text_area(
    "銘柄コード",
    value="5020\n5021\n5019",
    height=240,
    help="カンマ・改行・スペースで区切れます",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]

# しきい値（連載03 記事と統一）
REV_TH = 3.0   # 業績予想修正率 ±3%
RISE_TH = 2.0  # 値上り率 ±2%


# ── データロード ──────────────────────────────────────────────
try:
    df_all = load_universe()
except Exception as e:
    st.error(f"データ読み込みに失敗: {e}")
    st.stop()


# 入力コードでフィルタ
df = df_all[df_all["コード"].isin(tickers)].copy()
missing = [t for t in tickers if t not in df["コード"].values]


# ── メイン ──────────────────────────────────────────────
st.markdown("**⬛業績予想修正率 × 値上り率 4 象限マトリクス**")
st.caption(f" 修正率 ±{REV_TH:g}% / 値上り率（直近5営業日累計）±{RISE_TH:g}% で 4 象限を分類")

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

if missing:
    st.warning(f"見つからなかった銘柄コード: {', '.join(missing)}")

if df.empty:
    st.error("有効な銘柄が見つかりませんでした")
    st.stop()

# yfinance で値上り率取得 + merge
price_df = fetch_price_metrics(tuple(sorted(tickers)))
df = df.merge(price_df, on="コード", how="left")

missing_price = df[df["値上り率"].isna()]["コード"].tolist()
if missing_price:
    st.warning(f"株価データを取得できなかった銘柄: {', '.join(missing_price)}")

df_plot = df.dropna(subset=["業績予想修正率(予)", "値上り率"]).copy()
if df_plot.empty:
    st.error("プロット対象の銘柄がありません")
    st.stop()

# PER 計算
df_plot["PER予"] = df_plot["現在値"] / df_plot["EPS予"].where(df_plot["EPS予"] > 0)
df_plot["分類"] = classify_revision(df_plot, REV_TH, RISE_TH)


# ── 散布図 ──────────────────────────────────────────────
COLOR_MAP = {
    "🎯 出遅れ買い候補": "#27ae60",
    "🚨 逆行注意": "#e74c3c",
    "💨 既に反応済み": "#3498db",
    "⏳ 底入れ待ち": "#e67e22",
    "中立": "#888888",
}

XLIM = (-15.0, 15.0)
YLIM = (-10.0, 10.0)

df_plot["修正率_表示"] = df_plot["業績予想修正率(予)"].clip(lower=XLIM[0] + 0.3, upper=XLIM[1] - 0.3)
df_plot["値上り率_表示"] = df_plot["値上り率"].clip(lower=YLIM[0] + 0.3, upper=YLIM[1] - 0.3)
df_plot["ラベル"] = df_plot["コード"]

fig = px.scatter(
    df_plot,
    x="修正率_表示",
    y="値上り率_表示",
    color="分類",
    color_discrete_map=COLOR_MAP,
    text="ラベル",
    hover_data={
        "コード": True,
        "銘柄名": True,
        "業績予想修正率(予)": ":+.2f",
        "値上り率": ":+.2f",
        "PER予": ":.1f",
        "ROE": ":.1f",
        "時価総額": ":,.0f",
        "現在値": ":,.0f",
        "修正率_表示": False,
        "値上り率_表示": False,
        "分類": False,
        "ラベル": False,
    },
)
fig.update_traces(
    marker=dict(size=18, line=dict(width=1.5, color="white")),
    textposition="top center",
    textfont=dict(size=12, color="#202124"),
)
fig.update_xaxes(
    title="業績予想修正率(%) ← 下振れ　上振れ →",
    range=list(XLIM),
    tickvals=[-15, -10, -5, -3, 0, 3, 5, 10, 15],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)
fig.update_yaxes(
    title="値上り率(週次, %) ← 下落　上昇 →",
    range=list(YLIM),
    tickvals=[-10, -5, -2, 0, 2, 5, 10],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)

# 4 象限を薄い背景色で識別（右下=出遅れ買い候補=本命）
ZONE_FILL = [
    # (x0, x1, y0, y1, fillcolor)
    (REV_TH,  XLIM[1], YLIM[0],  -RISE_TH, "rgba(39, 174, 96, 0.10)"),    # 右下: 出遅れ買い候補
    (XLIM[0], -REV_TH, RISE_TH,  YLIM[1],  "rgba(231, 76, 60, 0.08)"),    # 左上: 逆行注意
    (REV_TH,  XLIM[1], RISE_TH,  YLIM[1],  "rgba(52, 152, 219, 0.08)"),   # 右上: 既反応済
    (XLIM[0], -REV_TH, YLIM[0],  -RISE_TH, "rgba(230, 126, 34, 0.08)"),   # 左下: 底入れ待ち
]
for x0, x1, y0, y1, color in ZONE_FILL:
    fig.add_shape(
        type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
        fillcolor=color, line=dict(width=0), layer="below",
    )
fig.add_vline(x=REV_TH,  line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)
fig.add_vline(x=-REV_TH, line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)
fig.add_hline(y=RISE_TH,  line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)
fig.add_hline(y=-RISE_TH, line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)

fig.update_layout(
    height=500,
    showlegend=False,
    margin=dict(t=30, b=40, l=40, r=20),
)

st.plotly_chart(fig, use_container_width=True)

_c1, _c2 = st.columns([2, 1])
with _c2:
    st.caption("ラベルは銘柄コード。ホバーで銘柄情報が確認できます")
    st.caption(
        """
**凡例**<br>
🟩 緑　出遅れ買い候補<br>
🟥 赤　逆行注意<br>
🟦 青　既に反応済み<br>
🟧 橙　底入れ待ち<br>
⬜ 灰　中立
""",
        unsafe_allow_html=True,
    )



# ── 詳細テーブル ──────────────────────────────────────────────
st.markdown("**⬛銘柄一覧**")
detail = df_plot[[
    "コード", "銘柄名", "業績予想修正率(予)", "値上り率", "PER予", "ROE", "時価総額", "現在値", "分類",
]].copy()
st.dataframe(
    detail.style.format({
        "業績予想修正率(予)": "{:+.2f}%",
        "値上り率": "{:+.2f}%",
        "PER予": "{:.1f}倍",
        "ROE": "{:.1f}%",
        "時価総額": "{:,.0f}",
        "現在値": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)
