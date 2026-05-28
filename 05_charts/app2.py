"""
連載05 Chart 2: 複数銘柄チャート比較（3列カードグリッド）

- 銘柄コードを複数入力（カンマ・スペース・改行区切り）
- 各カード: 銘柄名 / 価格 / 騰落率 / エリア塗り終値チャート(90日) / RSI・PER・PBR・配当 1行

ローカル前提: C:\\stock_analysis 配下の rakunav CSV を読みに行く（連載01 と同じ）。
データは利用規約により再配布しないため、各自の環境でセットアップしてください。

起動: streamlit run app2.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from config.paths import rakunav_file
from utils.master_names import apply_master_names


# ── ページ設定 + Wide / Narrow トグル ──────────────────────
st.set_page_config(
    page_title="複数銘柄チャート比較",
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


# ── rakunav CSV 読込（PER/PBR/配当利回り を計算） ──────────
RAKUNAV_SPECS = [
    (113, "EPS実績",  "EPS(一株あたり当期利益)"),
    (213, "EPS予想",  "EPS(予)(一株あたり当期利益)"),
    (215, "BPS予",   "BPS(予)(一株あたり純資産)"),
    (141, "配当金",   "配当金(円)"),
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
def load_metrics() -> pd.DataFrame:
    """rakunav 4 指標 + 現在値から PEG / PER / PBR / 配当利回り を計算。"""
    merged = None
    price_series = None
    for no, label, col_hint in RAKUNAV_SPECS:
        p = rakunav_file(no)
        if p is None:
            raise FileNotFoundError(f"rakunav/{no}_*.csv が見つかりません")
        df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.strip()
        cand = [c for c in df.columns if c == col_hint or c.startswith(col_hint)]
        df[label] = df[cand[0]].map(_to_float)
        if price_series is None and "現在値" in df.columns:
            price_series = df.set_index("コード")["現在値"].map(_to_float)
        d = df[["コード", "銘柄名", "市場", label]]
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )

    merged["現在値"]   = merged["コード"].map(price_series)
    merged["PER"]      = merged["現在値"] / merged["EPS予想"].where(merged["EPS予想"] > 0)
    merged["PBR"]      = merged["現在値"] / merged["BPS予"].where(merged["BPS予"] > 0)
    merged["配当利回り"] = (merged["配当金"] / merged["現在値"].where(merged["現在値"] > 0)) * 100

    merged = apply_master_names(merged)
    return merged.set_index("コード")


# ── yfinance 日足（90日 + RSI 計算用バッファ） ────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_daily(code: str, days: int = 90) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days + 30)  # RSI14 計算用バッファ
    df = yf.download(f"{code}.T", start=start, end=end + timedelta(days=1),
                     interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return df


def calc_rsi14(close: pd.Series) -> pd.Series:
    """Wilder の RSI(14)。"""
    diff = close.diff()
    gain = diff.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-diff.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.where(loss > 0)
    return 100 - 100 / (1 + rs)


# ── エリア（塗り）チャート ──────────────────────────────────
_N_BANDS = 6  # グラデーションの帯数


def _area_chart(df: pd.DataFrame, height: int = 200) -> go.Figure:
    """終値ライン + 下方向グラデーション塗り。上昇=緑/下落=赤。"""
    if df.empty:
        return go.Figure()

    # NaN を除外して期間の上昇/下落を判定（最新日に NaN が混じる場合に対応）
    valid = df["Close"].dropna()
    if len(valid) < 2:
        return go.Figure()
    first = float(valid.iloc[0])
    last  = float(valid.iloc[-1])
    is_up = last >= first
    line_color = "#1a9f3c" if is_up else "#e8372c"
    base_rgb   = (26, 159, 60) if is_up else (232, 55, 44)

    y_min = float(valid.min())
    y_max = float(valid.max())
    y_pad = (y_max - y_min) * 0.08
    y_floor = y_min - y_pad

    fig = go.Figure()
    # 透明ベース（fill の起点）
    fig.add_trace(go.Scatter(
        x=df["Date"], y=[y_floor] * len(df), mode="lines",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    # グラデーション帯
    y_arr = df["Close"].astype(float).tolist()
    for b in range(1, _N_BANDS + 1):
        ratio = b / _N_BANDS
        band_y = [y_floor + (c - y_floor) * ratio for c in y_arr]
        alpha = 0.04 + ratio * 0.18
        fig.add_trace(go.Scatter(
            x=df["Date"], y=band_y, mode="lines",
            line=dict(width=0, color="rgba(0,0,0,0)"),
            fill="tonexty",
            fillcolor=f"rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},{alpha:.3f})",
            showlegend=False, hoverinfo="skip",
        ))
    # 終値ライン
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"], mode="lines",
        line=dict(color=line_color, width=1.8),
        showlegend=False,
        hovertemplate="%{x|%Y/%m/%d}<br>%{y:,.0f}円<extra></extra>",
    ))
    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])],
        tickformat="%-m月", dtick="M1",
        tickfont=dict(size=14, color="#888"),
        showgrid=False, rangeslider_visible=False, showline=False,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#eeeeee", gridwidth=1,
        tickfont=dict(size=14, color="#888"),
        zeroline=False, showline=False, tickformat=",",
        range=[y_floor, y_max + y_pad],
    )
    fig.update_layout(
        height=height,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=4, r=4, t=4, b=4),
        showlegend=False,
    )
    return fig


# ── カード描画 ──────────────────────────────────────────────
def _fmt_metric(v, spec: str) -> str:
    return spec.format(v) if pd.notna(v) else "—"


def render_card(code: str, metrics: pd.DataFrame) -> None:
    df = load_daily(code, days=90)
    if df.empty:
        st.caption(f"{code}: チャートデータなし")
        return
    df_rsi = df.copy()
    df_rsi["RSI"] = calc_rsi14(df_rsi["Close"])
    df_show = df_rsi.tail(90).reset_index(drop=True)

    m = metrics.loc[code] if code in metrics.index else None
    name = m["銘柄名"] if m is not None else f"{code}.T"

    # 終値・期間騰落率（90日：最初の有効終値→最新の有効終値）
    valid = df_show.dropna(subset=["Close"])
    if valid.empty:
        st.caption(f"{code}: 有効な終値なし")
        return
    first = float(valid["Close"].iloc[0])
    last  = float(valid["Close"].iloc[-1])
    period_pct = (last - first) / first * 100 if first else 0.0
    chg_color = "#1a9f3c" if period_pct > 0 else "#e8372c" if period_pct < 0 else "#70757a"
    arrow = "↑" if period_pct > 0 else "↓" if period_pct < 0 else "→"
    sign  = "+" if period_pct > 0 else ""

    # ヘッダー: 銘柄名 + コード
    st.markdown(
        f"<div style='line-height:1.3;margin-bottom:2px'>"
        f"<span style='font-weight:700;font-size:1.2em;color:#202124'>{name}</span>"
        f"<span style='color:#70757a;font-size:0.8em'>　{code}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    # 価格 + 期間騰落率（90日）
    st.markdown(
        f"<div style='margin:4px 0 0'>"
        f"<span style='font-size:1.2em;color:#202124'>{last:,.0f}</span>"
        f"<span style='font-size:0.7em;color:#70757a;margin-left:4px'>円</span>"
        f"</div>"
        f"<div style='font-size:0.85em;color:{chg_color};margin-bottom:6px'>"
        f"{arrow} {sign}{period_pct:.2f}%（90日）</div>",
        unsafe_allow_html=True,
    )
    # エリアチャート
    st.plotly_chart(_area_chart(df_show), use_container_width=True,
                    config={"displayModeBar": False})

    # 1行小指標: RSI / PER / PBR / 配当
    rsi_val = df_rsi["RSI"].iloc[-1] if not df_rsi["RSI"].isna().all() else None
    parts = [f"RSI {_fmt_metric(rsi_val, '{:.1f}')}"]
    if m is not None:
        parts += [
            f"PER {_fmt_metric(m['PER'],  '{:.1f}')}",
            f"PBR {_fmt_metric(m['PBR'],  '{:.1f}')}",
            f"配当 {_fmt_metric(m['配当利回り'], '{:.2f}%')}",
        ]
    st.markdown(
        f"<div style='font-size:15px;color:#888;margin-top:-4px'>"
        f"{' / '.join(parts)}</div>",
        unsafe_allow_html=True,
    )


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("## 複数銘柄<br>チャート比較", unsafe_allow_html=True)
raw_codes = st.sidebar.text_area(
    "銘柄コード", value="8058\n8031\n8001\n8002\n8053\n8015\n2768\n8020",
    height=240, help="カンマ・改行・スペースで区切れます",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]
COLS_PER_ROW = 4


# ── データロード ──────────────────────────────────────────
try:
    metrics = load_metrics()
except Exception as e:
    st.error(f"rakunav 読み込みに失敗: {e}")
    st.stop()

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()


# ── 3列カードグリッド ───────────────────────────────────────
for i in range(0, len(tickers), COLS_PER_ROW):
    chunk = tickers[i: i + COLS_PER_ROW]
    cols = st.columns(COLS_PER_ROW, gap="medium")
    for j, col in enumerate(cols):
        if j >= len(chunk):
            continue
        with col:
            render_card(chunk[j], metrics)
