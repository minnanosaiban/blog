"""
連載05 Chart 1: 5分足ローソク + 日足ライン（複数銘柄）

- 銘柄コードを改行・カンマ・スペースで区切って複数入力
- 5分足ローソク（縦の境界線でギャップ可視化）+ 日足ラインを Altair で表示
- 当日終値は yfinance.fast_info で上書き（5分足の末尾と公式引け値のズレを補正）

起動: streamlit run app1.py
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta

import altair as alt
import pandas as pd
import streamlit as st
import yfinance as yf


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

# Y 軸ラベル幅（左揃え用）
Y_MIN_EXTENT = 50


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


# ── チャート定義 ────────────────────────────────────────────
def daily_line_chart(df_daily: pd.DataFrame) -> alt.Chart:
    """日足の終値ライン（右上の小さなチャート用）。"""
    df = df_daily.reset_index().rename(columns={"index": "Date"})[["Date", "Close"]]
    return (
        alt.Chart(df)
        .mark_line(color="#FF4B4B", strokeWidth=1.5)
        .encode(
            x=alt.X("Date:T", title=None, axis=alt.Axis(format="%m月", grid=False)),
            y=alt.Y("Close:Q", title=None, scale=alt.Scale(zero=False),
                    axis=alt.Axis(minExtent=Y_MIN_EXTENT)),
            tooltip=["Date", "Close"],
        )
        .properties(height=200)
    )


def candle_chart(df_5min: pd.DataFrame) -> alt.VConcatChart:
    """5分足ローソク + 出来高（日の境界線つき）。"""
    df = df_5min.copy()
    df["x"]    = df["Datetime"].dt.strftime("%y/%m/%d %H:%M")
    df["VolK"] = df["Volume"] / 1000
    df["date"] = df["Datetime"].dt.date
    # その日最初の足（朝寄り）と昼寄り（12:30）にマーカー用のフラグを立てる
    df["is_am"] = df["Datetime"] == df.groupby("date")["Datetime"].transform("min")
    df["is_pm"] = df["Datetime"].dt.time == time(12, 30)
    tick_xs = df[df["is_am"] | df["is_pm"]]["x"].unique().tolist()

    # Y 軸: 高安に少し余白を持たせる
    lo, hi = df["Close"].min(), df["Close"].max()
    y_scale = alt.Scale(
        domain=[float(lo - (hi - lo) * 0.05), float(hi + (hi - lo) * 0.05)],
        zero=False,
    )

    # 上昇は赤、下落は緑（日本式）
    color = alt.condition(
        "datum.Open <= datum.Close",
        alt.value("#ef5350"),
        alt.value("#26a69a"),
    )

    base = alt.Chart(df).encode(
        x=alt.X("x:O", sort=None, axis=alt.Axis(
            labels=False, values=tick_xs, grid=False, title=None,
        )),
    )

    # 日付境界の縦線（午前=濃いめ、午後=薄め）
    rule_am = alt.Chart(df[df["is_am"]]).mark_rule(color="#CCCCCC").encode(x="x:O")
    rule_pm = alt.Chart(df[df["is_pm"]]).mark_rule(color="#EEEEEE").encode(x="x:O")

    # ローソク本体（ヒゲ）
    wick = base.mark_rule().encode(
        y=alt.Y("Low:Q", scale=y_scale,
                axis=alt.Axis(minExtent=Y_MIN_EXTENT, title=None)),
        y2="High:Q",
        color=color,
    )
    body = base.mark_bar().encode(y="Open:Q", y2="Close:Q", color=color)
    candle = alt.layer(rule_am, rule_pm, wick, body)

    # 出来高サブパネル
    volume = base.mark_bar(opacity=0.5).encode(
        y=alt.Y("VolK:Q",
                axis=alt.Axis(orient="left", minExtent=Y_MIN_EXTENT, title=None)),
        color=color,
    ).properties(height=80)

    return alt.vconcat(candle, volume).resolve_scale(x="shared").configure_view(strokeOpacity=0)


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
        st.altair_chart(daily_line_chart(df_daily), width="stretch")

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
    st.altair_chart(candle_chart(df_5min), width="stretch")

    # 騰落率＋終値テーブル
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
