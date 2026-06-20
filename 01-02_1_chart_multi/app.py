"""
連載05 Chart 2: 複数銘柄チャート比較（4列カードグリッド）

- 銘柄コードを複数入力（カンマ・スペース・改行区切り）
- 各カード: 銘柄名 / 価格 / 騰落率 / エリア塗り終値チャート(90日) / RSI・指標1行
- 日足データ : data/prices/daily/{code}.parquet
- 業績指標   : data/{113,213,215,141}_*.csv（楽天MS2 CSVを手動配置）

起動: streamlit run 02_multi_chart/app.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
COLS_PER_ROW = 4


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="日足チャート",
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


# ── 業績指標（楽天MS2 CSV） ─────────────────────────────────
_RAKUNAV = {
    "EPS実績": ("113_EPS.csv",   "EPS(一株あたり当期利益)"),
    "EPS予想": ("213_EPS.csv",   "EPS(予)(一株あたり当期利益)"),
    "BPS予":   ("215_BPS.csv",   "BPS(予)(一株あたり純資産)"),
    "配当金":  ("141_配当金.csv", "配当金(円)"),
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


@st.cache_data(ttl=3600, show_spinner=False)
def load_metrics() -> pd.DataFrame | None:
    """data/ 以下の楽天MS2 CSV を結合して返す。ファイルがなければ None。"""
    merged = None
    price_series = None
    for label, (fname, col_hint) in _RAKUNAV.items():
        path = DATA_DIR / fname
        if not path.exists():
            return None
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        df["コード"] = df["コード"].astype(str).str.zfill(4).str.strip()
        cand = [c for c in df.columns if c == col_hint or c.startswith(col_hint)]
        if not cand:
            return None
        df[label] = df[cand[0]].map(_to_float)
        if price_series is None and "現在値" in df.columns:
            price_series = df.set_index("コード")["現在値"].map(_to_float)
        keep = [c for c in ["コード", "銘柄名", "市場", label] if c in df.columns]
        d = df[keep]
        merged = d if merged is None else merged.merge(d, on=["コード", "銘柄名", "市場"], how="outer")

    if merged is None:
        return None
    if price_series is not None:
        merged["現在値"] = merged["コード"].map(price_series)
    merged["PER"]       = merged["現在値"] / merged["EPS予想"].where(merged["EPS予想"] > 0)
    merged["PBR"]       = merged["現在値"] / merged["BPS予"].where(merged["BPS予"] > 0)
    merged["配当利回り"] = (merged["配当金"] / merged["現在値"].where(merged["現在値"] > 0)) * 100
    return merged.set_index("コード")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_master() -> pd.DataFrame:
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
def get_name(code: str, metrics: pd.DataFrame | None) -> str:
    if metrics is not None and code in metrics.index:
        val = metrics.loc[code, "銘柄名"]
        if pd.notna(val):
            return str(val)
    master = _load_master()
    if not master.empty:
        row = master[master["コード"] == str(code).zfill(4)]
        if not row.empty:
            r = row.iloc[0]
            for col in ("銘柄", "銘柄名"):
                val = r.get(col, None)
                if pd.notna(val) and val:
                    return str(val)
    return code


# ── 日足 parquet 読込 ───────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_daily(code: str, days: int = 120) -> pd.DataFrame:
    """日足 parquet から直近 days 行を返す（RSI バッファ込み）。"""
    path = DATA_DIR / "prices" / "daily" / f"{code}.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.sort_index().tail(days).reset_index()
    df = df.rename(columns={df.columns[0]: "Date"})
    return df


# ── チャート・指標ヘルパー ──────────────────────────────────
_N_BANDS = 6


def calc_rsi14(close: pd.Series) -> pd.Series:
    diff = close.diff()
    gain = diff.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-diff.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.where(loss > 0)
    return 100 - 100 / (1 + rs)


def _area_chart(df: pd.DataFrame, height: int = 200) -> go.Figure:
    if df.empty:
        return go.Figure()
    valid = df["Close"].dropna()
    if len(valid) < 2:
        return go.Figure()
    first, last = float(valid.iloc[0]), float(valid.iloc[-1])
    is_up      = last >= first
    line_color = "#1a9f3c" if is_up else "#e8372c"
    base_rgb   = (26, 159, 60) if is_up else (232, 55, 44)
    y_min, y_max = float(valid.min()), float(valid.max())
    y_pad   = (y_max - y_min) * 0.08
    y_floor = y_min - y_pad

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=[y_floor] * len(df), mode="lines",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    y_arr = df["Close"].astype(float).tolist()
    for b in range(1, _N_BANDS + 1):
        ratio = b / _N_BANDS
        alpha = 0.04 + ratio * 0.18
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=[y_floor + (c - y_floor) * ratio for c in y_arr],
            mode="lines",
            line=dict(width=0, color="rgba(0,0,0,0)"),
            fill="tonexty",
            fillcolor=f"rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},{alpha:.3f})",
            showlegend=False, hoverinfo="skip",
        ))
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


def _fmt(v, spec: str) -> str:
    return spec.format(v) if pd.notna(v) else "—"


def render_card(code: str, metrics: pd.DataFrame | None) -> None:
    df = load_daily(code, days=120)
    if df.empty:
        st.caption(f"{code}: データなし（先に「データ取得」で保存してください）")
        return
    df["RSI"] = calc_rsi14(df["Close"])
    df_show   = df.tail(90).reset_index(drop=True)

    m    = metrics.loc[code] if (metrics is not None and code in metrics.index) else None
    name = get_name(code, metrics)

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

    st.markdown(
        f"<div style='line-height:1.3;margin-bottom:2px'>"
        f"<span style='font-weight:700;font-size:1.2em;color:#202124'>{name}</span>"
        f"<span style='color:#70757a;font-size:0.8em'>　{code}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='margin:4px 0 0'>"
        f"<span style='font-size:1.2em;color:#202124'>{last:,.0f}</span>"
        f"<span style='font-size:0.7em;color:#70757a;margin-left:4px'>円</span>"
        f"</div>"
        f"<div style='font-size:0.85em;color:{chg_color};margin-bottom:6px'>"
        f"{arrow} {sign}{period_pct:.2f}%（90日）</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(_area_chart(df_show), use_container_width=True,
                    config={"displayModeBar": False})

    rsi_val  = df["RSI"].iloc[-1] if not df["RSI"].isna().all() else None
    ma25     = df["Close"].rolling(25).mean().iloc[-1]
    ma25_dev = (last - float(ma25)) / float(ma25) * 100 if pd.notna(ma25) and float(ma25) > 0 else None
    ma25_str = f"{'+'if (ma25_dev or 0) >= 0 else ''}{ma25_dev:.1f}%" if ma25_dev is not None else "(—)"

    row1 = [f"RSI {_fmt(rsi_val, '{:.1f}')}", f"25MA {ma25_str}"]
    row2: list[str] = []
    if m is not None:
        roe = (m["EPS予想"] / m["BPS予"] * 100
               if pd.notna(m.get("EPS予想")) and pd.notna(m.get("BPS予")) and m["BPS予"] > 0
               else None)
        row1.append(f"配当 {_fmt(m['配当利回り'], '{:.2f}%')}")
        row2 += [f"ROE {_fmt(roe, '{:.1f}%')}", f"PER {_fmt(m['PER'], '{:.1f}')}",
                 f"PBR {_fmt(m['PBR'], '{:.1f}')}"]
    st.markdown(
        f"<div style='font-size:15px;color:#888;margin-top:-4px;line-height:1.6'>"
        f"{' / '.join(row1)}"
        + (f"<br>{' / '.join(row2)}" if row2 else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.checkbox("Wide 表示", key="_wide_layout")
st.sidebar.markdown("# 日足チャート", unsafe_allow_html=True)
today_obj = datetime.now()
today_str = f"{today_obj.year}年{today_obj.month}月{today_obj.day}日"
st.sidebar.caption(today_str)
st.sidebar.divider()

# ── チャート表示 ────────────────────────────────────────────
st.sidebar.markdown("### ⬛ チャート表示")

raw_codes = st.sidebar.text_area(
    "銘柄コード（改行 / スペース / カンマ区切り）",
    value="8058\n8031\n8001\n8002\n8053\n8015\n2768\n8020",
    height=160,
    help="カンマ・改行・スペース区切りで複数入力可",
)
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
        value="8058\n8031\n8001",
        height=68,
        disabled=is_topix,
    )

    @st.cache_data(ttl=3600, show_spinner=False)
    def _load_topix500() -> list[str]:
        master = _load_master()
        if master.empty:
            return []
        col_size = next((c for c in master.columns if "規模" in c and "区分" in c), None)
        col_code = next((c for c in master.columns
                         if "コード" in c and "ティッカー" not in c
                         and "33" not in c and "17" not in c and "セクター" not in c), None)
        if not col_size or not col_code:
            return []
        targets = ["TOPIX Core30", "TOPIX Large70", "TOPIX Mid400"]
        return sorted(master[master[col_size].isin(targets)][col_code]
                      .dropna().astype(str).str.strip().tolist())

    t500 = _load_topix500()
    st.text_input(
        "TOPIX500 対象銘柄数",
        value=f"{len(t500)} 銘柄" if is_topix else "―",
        disabled=not is_topix,
    )
    fetch_mode = st.radio(
        "取得範囲",
        ["日足2年", "日足5日"],
        horizontal=True,
    )
    btn_fetch = st.button("株価を取得", use_container_width=True)

st.sidebar.divider()

# ── メイン ──────────────────────────────────────────────────
if btn_fetch:
    fetch_tickers = (
        t500 if is_topix
        else [t.strip() for t in re.split(r"[,\s\n]+", fetch_raw) if t.strip()]
    )
    if not fetch_tickers:
        st.warning("銘柄コードを入力してください。")
    else:
        try:
            _app_dir = str(Path(__file__).parent)
            if _app_dir not in sys.path:
                sys.path.insert(0, _app_dir)
            from fetch_prices import fetch_one
            p_daily = "2y" if fetch_mode == "日足2年" else "5d"
            ok = err = 0
            bar = st.progress(0, text="yfinance からデータ取得中...")
            for i, c in enumerate(fetch_tickers):
                bar.progress(
                    (i + 1) / len(fetch_tickers),
                    text=f"取得中 {i + 1}/{len(fetch_tickers)}: {c}",
                )
                try:
                    fetch_one(c, period_daily=p_daily)
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
        metrics = load_metrics()
        for i in range(0, len(chart_tickers), COLS_PER_ROW):
            chunk = chart_tickers[i: i + COLS_PER_ROW]
            cols  = st.columns(COLS_PER_ROW, gap="medium")
            for j, col in enumerate(cols):
                if j >= len(chunk):
                    continue
                with col:
                    render_card(chunk[j], metrics)

else:
    st.info("👈 銘柄コードを入力し「チャート表示」を押してください")
