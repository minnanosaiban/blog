"""
連載 Chart 1: 5分足ローソク + 騰落率テーブル（複数銘柄）

- 銘柄コードを改行・カンマ・スペースで区切って複数入力
- 5分足ローソク（縦の境界線でギャップ可視化）+ 出来高 + 日足ラインを Plotly で表示
- 株価チャートと日次の騰落率テーブルを日付を揃えて並べる
- 当日終値は yfinance.fast_info で上書き（5分足の末尾と公式引け値のズレを補正）

起動: streamlit run app1.py
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


# ── ページ設定 + Wide / Narrow トグル ──────────────────────
st.set_page_config(
    page_title="5分足チャート",
    page_icon="📈",
    layout="wide",
)

_NARROW_CSS = """<style>
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1100px !important;
    padding-left: 2rem !important; padding-right: 2rem !important;
    margin-left: auto !important; margin-right: auto !important;
}
</style>"""
st.session_state.setdefault("_wide_layout", False)
st.sidebar.checkbox("Wide 表示", key="_wide_layout")
if not st.session_state["_wide_layout"]:
    st.markdown(_NARROW_CSS, unsafe_allow_html=True)

# 上昇は赤、下落は緑（日本式）
C_UP = "#ef5350"
C_DOWN = "#26a69a"


# ── データ取得 ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_name(code: str) -> str:
    """yfinance.Search で銘柄名を取得。失敗時はコードのみ返す。"""
    try:
        quotes = yf.Search(f"{code}.T", max_results=1).quotes
        if not quotes:
            return f"{code}.T"
        return quotes[0].get("shortname") or f"{code}.T"
    except Exception:
        return f"{code}.T"


@st.cache_data(ttl=300)
def load_stock(code: str, end_dt: datetime, days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """5分足（直近 days 営業日分）と日足（180日分）を取得。"""
    symbol = f"{code}.T"

    # 5分足: 45日分を取得してから直近 days 営業日を残す
    df_5min = yf.download(
        symbol,
        start=end_dt - timedelta(days=45),
        end=end_dt + timedelta(days=1),
        interval="5m",
        progress=False,
        auto_adjust=True,
    )
    # 日足: MA・前日比計算用に180日分
    df_daily = yf.download(
        symbol,
        start=end_dt - timedelta(days=180),
        end=end_dt + timedelta(days=1),
        interval="1d",
        progress=False,
        auto_adjust=True,
    )

    if df_5min.empty or df_daily.empty:
        return pd.DataFrame(), pd.DataFrame()

    # yfinance が MultiIndex で返すケースに対応
    for d in (df_5min, df_daily):
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)

    # 5分足: 日本時間に変換、直近 days 営業日に絞る
    df_5min = df_5min.reset_index()
    dt_col = df_5min.get("Datetime", df_5min.get("Date"))
    df_5min["Datetime"] = pd.to_datetime(dt_col).dt.tz_convert("Asia/Tokyo")
    recent_dates = sorted(df_5min["Datetime"].dt.date.unique(), reverse=True)[:days]
    df_5min = df_5min[df_5min["Datetime"].dt.date.isin(recent_dates)]
    df_5min = df_5min.sort_values("Datetime")

    df_daily.index = pd.to_datetime(df_daily.index).date

    return df_5min, df_daily


# ── チャート定義（Plotly） ──────────────────────────────────
def daily_line_fig(df_daily: pd.DataFrame) -> go.Figure:
    """日足の終値ライン（右上の小さなチャート用）。"""
    df = df_daily.reset_index().rename(columns={"index": "Date"})[["Date", "Close"]]
    fig = go.Figure(go.Scatter(
        x=df["Date"], y=df["Close"], mode="lines",
        line=dict(color="#FF4B4B", width=1.5),
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.1f}<extra></extra>",
    ))
    fig.update_layout(
        height=200, margin=dict(l=46, r=10, t=10, b=20),
        showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(title=None, tickformat="%-m月", showgrid=False)
    fig.update_yaxes(title=None)
    return fig


def candle_fig(df_5min: pd.DataFrame) -> go.Figure:
    """5分足ローソク + 出来高（日の境界線つき）。"""
    df = df_5min.copy()
    df["x"]    = df["Datetime"].dt.strftime("%y/%m/%d %H:%M")
    df["VolK"] = df["Volume"] / 1000
    df["date"] = df["Datetime"].dt.date
    # その日最初の足（朝寄り）と昼寄り（12:30）にフラグを立てる
    df["is_am"] = df["Datetime"] == df.groupby("date")["Datetime"].transform("min")
    df["is_pm"] = df["Datetime"].dt.time == time(12, 30)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.74, 0.26], vertical_spacing=0.02,
    )

    # ローソク本体
    fig.add_trace(go.Candlestick(
        x=df["x"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color=C_UP), fillcolor=C_UP),
        decreasing=dict(line=dict(color=C_DOWN), fillcolor=C_DOWN),
        showlegend=False, name="",
    ), row=1, col=1)

    # 出来高
    vol_color = [C_UP if o <= c else C_DOWN for o, c in zip(df["Open"], df["Close"])]
    fig.add_trace(go.Bar(
        x=df["x"], y=df["VolK"], marker_color=vol_color, opacity=0.5,
        showlegend=False, name="",
    ), row=2, col=1)

    # 日付境界の縦線（午前=濃いめ / 午後=薄め）― チャート全体を貫く
    for xv in df.loc[df["is_am"], "x"]:
        fig.add_vline(x=xv, line=dict(color="#CCCCCC", width=1))
    for xv in df.loc[df["is_pm"], "x"]:
        fig.add_vline(x=xv, line=dict(color="#EEEEEE", width=1))

    # 朝寄りの位置にだけ日付ラベルを表示
    am_x = df.loc[df["is_am"], "x"].tolist()
    am_label = df.loc[df["is_am"], "Datetime"].dt.strftime("%m/%d").tolist()

    # Y 軸（高安に少し余白）
    lo, hi = float(df["Low"].min()), float(df["High"].max())
    pad = (hi - lo) * 0.05

    fig.update_layout(
        height=460, margin=dict(l=46, r=10, t=10, b=24),
        xaxis_rangeslider_visible=False,
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        bargap=0,
    )
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(tickmode="array", tickvals=am_x, ticktext=am_label,
                     tickangle=0, row=2, col=1)
    fig.update_yaxes(range=[lo - pad, hi + pad], row=1, col=1)
    fig.update_yaxes(title=None)
    return fig


# ── 1銘柄ぶんの描画 ─────────────────────────────────────────
def render_ticker(code: str, df_5min: pd.DataFrame, df_daily: pd.DataFrame, name: str) -> None:
    # 最新値（fast_info） ― 当日表示と「未確定日の終値」上書きに使う
    last_price: float | None = None
    try:
        v = yf.Ticker(f"{code}.T").fast_info.get("lastPrice")
        last_price = float(v) if v else None
    except Exception:
        pass

    # ヘッダー: 銘柄名・最新値・期間中の最大/最小
    col_head, _, col_mini = st.columns([2, 1, 1])
    with col_head:
        st.subheader(f"{code} {name}")
        if last_price:
            if last_price == int(last_price):
                st.subheader(f"{int(last_price):,}")
            else:
                st.subheader(f"{last_price:,.1f}")
        st.caption(f"📈 Max: {df_5min['High'].max():,.1f} JPY　　"
                   f"📉 Min: {df_5min['Low'].min():,.1f} JPY")
    with col_mini:
        st.plotly_chart(daily_line_fig(df_daily), use_container_width=True)

    # 5分足を日次に集約し、可能なところは日足で上書き（精度補正）
    by_day = df_5min.groupby(df_5min["Datetime"].dt.date).agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
    ).sort_index()
    daily_valid = df_daily.dropna(subset=["Close"])
    common = by_day.index.intersection(daily_valid.index)
    if len(common):
        by_day.loc[common, ["Open", "High", "Low", "Close"]] = \
            daily_valid.loc[common, ["Open", "High", "Low", "Close"]].values

    # 当日（dfd未確定）の終値は fast_info で上書き
    if last_price and len(by_day) > 0:
        last_day = by_day.index[-1]
        if last_day not in daily_valid.index:
            by_day.loc[last_day, "Close"] = last_price

    # 騰落率テーブル
    prev_close = df_daily["Close"].shift(1)

    def chg_str(d) -> str:
        if d not in prev_close.index or pd.isna(prev_close.loc[d]):
            return "-"
        pct = (by_day.loc[d, "Close"] - prev_close.loc[d]) / prev_close.loc[d] * 100
        mark = "🔴" if pct > 0 else "🟢" if pct < 0 else ""
        return f"{mark}{pct:+.2f}%"

    by_day["騰落率"] = [chg_str(d) for d in by_day.index]

    # 5分足ローソク
    st.plotly_chart(candle_fig(df_5min), use_container_width=True)

    # 騰落率＋終値テーブル（チャートと日付を揃える）
    table = by_day[["騰落率", "Close"]].rename(columns={"Close": "終値"})
    table.index = [d.strftime("%m/%d") for d in table.index]
    table["終値"] = table["終値"].apply(lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) else x)
    st.dataframe(table.T, width="stretch")


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("## 5分足チャート")

raw_codes = st.sidebar.text_area("銘柄コード", value="5020", height=160)
days      = st.sidebar.number_input("遡る日数", min_value=1, max_value=60, value=15, step=1)
tickers   = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]

# 表のセル余白を詰める
st.markdown("<style>.stDataFrame div{border-radius:0px;}</style>", unsafe_allow_html=True)


# ── メイン ──────────────────────────────────────────────────
end_date = datetime.now()
for ticker in tickers:
    df_5min, df_daily = load_stock(ticker, end_date, days)
    if df_5min.empty:
        st.warning(f"{ticker}: 株価データが取得できません")
        continue
    render_ticker(ticker, df_5min, df_daily, get_name(ticker))
