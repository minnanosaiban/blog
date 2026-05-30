"""
連載 Chart 1: 5分足ローソク + 騰落率テーブル（複数銘柄）

- 銘柄コードを改行・カンマ・スペースで区切って複数入力、または TOPIX500 全銘柄を選択
- 5分足ローソク（縦の境界線でギャップ可視化）+ 出来高 + 日足ラインを Plotly で表示
- 株価チャートと日次の騰落率テーブルを日付を揃えて並べる
- データは data/prices/{5min|daily}/{code}.parquet を使用

起動: streamlit run 01_5min_chart/app.py
"""
from __future__ import annotations

import re
from datetime import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DATA_DIR = Path(__file__).parent / "data"

# ── ページ設定 ──────────────────────────────────────────────
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
if not st.session_state["_wide_layout"]:
    st.markdown(_NARROW_CSS, unsafe_allow_html=True)

# 上昇は赤、下落は緑（日本式）
C_UP   = "#ef5350"
C_DOWN = "#26a69a"


# ── マスタ読み込み ──────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _load_master() -> pd.DataFrame:
    """data_j.xls（JPX・規模区分）と stocks.csv（銘柄名）を結合して返す。"""
    master_dir = DATA_DIR / "master"
    xls_path   = master_dir / "data_j.xls"
    stocs_path = master_dir / "stocks.csv"

    df = pd.DataFrame()
    if xls_path.exists():
        df = pd.read_excel(xls_path, dtype={"コード": str})
        df["コード"] = df["コード"].astype(str).str.zfill(4)

    if stocs_path.exists():
        df_s = pd.read_csv(stocs_path, dtype={"コード": str}, encoding="utf-8-sig")
        df_s["コード"] = df_s["コード"].astype(str).str.zfill(4)
        df = df.merge(df_s, on="コード", how="left") if not df.empty else df_s

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def get_name(code: str) -> str:
    """マスタCSV の「銘柄」列から銘柄名を返す。未収録時はコードのみ。"""
    master = _load_master()
    row = master[master["コード"] == str(code)]
    if row.empty:
        return code
    val = row.iloc[0].get("銘柄", None)
    return str(val) if val else code


@st.cache_data(ttl=3600, show_spinner=False)
def load_topix500_codes() -> list[str]:
    master = _load_master()
    col_size = next((c for c in master.columns if "規模" in c and "区分" in c), None)
    col_code = next((c for c in master.columns
                     if "コード" in c
                     and "ティッカー" not in c
                     and "33" not in c
                     and "17" not in c
                     and "セクター" not in c), None)
    if not col_size or not col_code:
        return []
    targets = ["TOPIX Core30", "TOPIX Large70", "TOPIX Mid400"]
    return sorted(
        master[master[col_size].isin(targets)][col_code]
        .dropna().astype(str).str.strip().tolist()
    )


# ── データ取得 ──────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_stock(code: str, days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """5分足（直近 days 営業日分）と日足を Parquet から取得。"""
    path_5min  = DATA_DIR / "prices" / "5min"  / f"{code}.parquet"
    path_daily = DATA_DIR / "prices" / "daily" / f"{code}.parquet"

    if not path_5min.exists() or not path_daily.exists():
        return pd.DataFrame(), pd.DataFrame()

    # ── 5分足 ──
    df_5min = pd.read_parquet(path_5min)
    if isinstance(df_5min.columns, pd.MultiIndex):
        df_5min.columns = df_5min.columns.get_level_values(0)
    df_5min = df_5min.reset_index()
    dt_col = df_5min.columns[0]
    df_5min["Datetime"] = pd.to_datetime(df_5min[dt_col]).dt.tz_convert("Asia/Tokyo")
    if dt_col != "Datetime":
        df_5min = df_5min.drop(columns=[dt_col])
    df_5min["_date"] = df_5min["Datetime"].dt.date
    recent_dates = sorted(df_5min["_date"].unique(), reverse=True)[:days]
    df_5min = df_5min[df_5min["_date"].isin(recent_dates)].drop(columns=["_date"]).sort_values("Datetime")

    # ── 日足 ──
    df_daily = pd.read_parquet(path_daily)
    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)
    df_daily.index = pd.to_datetime(df_daily.index).date

    return df_5min, df_daily


# ── チャート定義（Plotly） ──────────────────────────────────
def daily_line_fig(df_daily: pd.DataFrame) -> go.Figure:
    """日足の終値ライン（直近6か月・右上の小さなチャート用）。"""
    df = df_daily.reset_index().rename(columns={"index": "Date"})[["Date", "Close"]]
    df = df.tail(126)  # 約6か月分（営業日ベース）
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
    df["is_am"] = df["Datetime"] == df.groupby("date")["Datetime"].transform("min")
    df["is_pm"] = df["Datetime"].dt.time == time(12, 30)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.74, 0.26], vertical_spacing=0.02,
    )
    fig.add_trace(go.Candlestick(
        x=df["x"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color=C_UP), fillcolor=C_UP),
        decreasing=dict(line=dict(color=C_DOWN), fillcolor=C_DOWN),
        showlegend=False, name="",
    ), row=1, col=1)

    vol_color = [C_UP if o <= c else C_DOWN for o, c in zip(df["Open"], df["Close"])]
    fig.add_trace(go.Bar(
        x=df["x"], y=df["VolK"], marker_color=vol_color, opacity=0.5,
        showlegend=False, name="",
    ), row=2, col=1)

    for xv in df.loc[df["is_am"], "x"]:
        fig.add_vline(x=xv, line=dict(color="#CCCCCC", width=1))
    for xv in df.loc[df["is_pm"], "x"]:
        fig.add_vline(x=xv, line=dict(color="#EEEEEE", width=1))

    am_x     = df.loc[df["is_am"], "x"].tolist()
    am_label = df.loc[df["is_am"], "Datetime"].dt.strftime("%m/%d").tolist()
    lo, hi   = float(df["Low"].min()), float(df["High"].max())
    pad      = (hi - lo) * 0.05

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
    last_price = float(df_5min["Close"].iloc[-1]) if not df_5min.empty else None

    col_head, _, col_mini = st.columns([2, 1, 1])
    with col_head:
        st.subheader(f"{code} {name}")
        if last_price is not None:
            if last_price == int(last_price):
                st.subheader(f"{int(last_price):,}")
            else:
                st.subheader(f"{last_price:,.1f}")
        st.caption(f"📈 Max: {df_5min['High'].max():,.1f} JPY　　"
                   f"📉 Min: {df_5min['Low'].min():,.1f} JPY")
    with col_mini:
        st.plotly_chart(daily_line_fig(df_daily), use_container_width=True)

    # 5分足を日次に集約し、日足で上書き（精度補正）
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

    # 騰落率テーブル
    prev_close = df_daily["Close"].shift(1)

    def chg_str(d) -> str:
        if d not in prev_close.index or pd.isna(prev_close.loc[d]):
            return "-"
        pct = (by_day.loc[d, "Close"] - prev_close.loc[d]) / prev_close.loc[d] * 100
        mark = "🔴" if pct > 0 else "🟢" if pct < 0 else ""
        return f"{mark}{pct:+.2f}%"

    by_day["騰落率"] = [chg_str(d) for d in by_day.index]

    st.plotly_chart(candle_fig(df_5min), use_container_width=True)

    table = by_day[["騰落率", "Close"]].rename(columns={"Close": "終値"})
    table.index = [d.strftime("%m/%d") for d in table.index]
    table["終値"] = table["終値"].apply(
        lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) else x
    )
    st.dataframe(table.T, width="stretch")


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.checkbox("Wide 表示", key="_wide_layout")
st.sidebar.markdown("# 5分足チャート", unsafe_allow_html=True)
st.sidebar.divider()

# ── チャート表示 ────────────────────────────────────────────
st.sidebar.markdown("### ⬛ チャート表示")

raw_codes = st.sidebar.text_area(
    "銘柄コード（改行 / スペース / カンマ区切り）",
    value="5020",
    height=68,
    help="カンマ・改行・スペース区切りで複数入力可",
)
days_str = st.sidebar.text_input("遡る日数", value="12")
try:
    days = max(1, min(60, int(days_str)))
except ValueError:
    days = 12

btn_show = st.sidebar.button("チャート表示", use_container_width=True)

st.sidebar.divider()

# ── データ取得 ──────────────────────────────────────────────
st.sidebar.markdown("### ⬛ 株価 Parquet 取得")

with st.sidebar.expander("データ取得"):
    mode     = st.radio("銘柄選択", ["銘柄コード指定", "TOPIX500"],
                        horizontal=True, key="_data_mode")
    is_topix = mode == "TOPIX500"

    fetch_raw = st.text_area(
        "銘柄コード",
        value="5020",
        height=68,
        disabled=is_topix,
    )
    t500_codes = load_topix500_codes()
    st.text_input(
        "TOPIX500 対象銘柄数",
        value=f"{len(t500_codes)} 銘柄" if is_topix else "―",
        disabled=not is_topix,
    )

    fetch_mode = st.radio(
        "取得範囲",
        ["日足2年・5分足60日", "日足5日・5分足3日"],
        horizontal=True,
    )
    btn_fetch = st.button("株価を取得", use_container_width=True)

# 表のセル余白を詰める
st.markdown("<style>.stDataFrame div{border-radius:0px;}</style>", unsafe_allow_html=True)

st.sidebar.divider()

# ── メイン ──────────────────────────────────────────────────
if btn_fetch:
    fetch_tickers = (
        t500_codes if is_topix
        else [t.strip() for t in re.split(r"[,\s\n]+", fetch_raw) if t.strip()]
    )
    if not fetch_tickers:
        st.warning("銘柄コードを入力してください。")
    else:
        try:
            from fetch_prices import fetch_one
            p_daily, p_5min = (
                ("2y", "60d") if fetch_mode == "日足2年・5分足60日" else ("5d", "3d")
            )
            ok = err = 0
            bar = st.progress(0, text="yfinance からデータ取得中...")
            for i, c in enumerate(fetch_tickers):
                bar.progress(
                    (i + 1) / len(fetch_tickers),
                    text=f"取得中 {i + 1}/{len(fetch_tickers)}: {c}",
                )
                try:
                    fetch_one(c, period_daily=p_daily, period_5min=p_5min)
                    ok += 1
                except Exception:
                    err += 1
            bar.empty()
            st.success(f"取得完了: {ok} 銘柄成功 / {err} 失敗 → `data/prices/`")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"取得に失敗しました: {e}")

elif btn_show:
    chart_tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]
    if not chart_tickers:
        st.warning("銘柄コードを入力してください。")
    else:
        for ticker in chart_tickers:
            df_5min, df_daily = load_stock(ticker, days)
            if df_5min.empty:
                st.warning(f"{ticker}: データが見つかりません（先に「データ取得」で保存してください）")
                continue
            render_ticker(ticker, df_5min, df_daily, get_name(ticker))

else:
    st.info("👈 銘柄コードを入力し「チャート表示」を押してください")
