"""
連載05 Chart 3: 決算パターングリッド簡素版（5分足エリアチャート）

- 同梱の earnings.csv（date,time,code）から発表銘柄を集計
- 発表後の値動きを SNS 5 パターンに分類（上げ / 逆V字 / 無風 / V字 / 下げ）
- 選択パターンの銘柄を 3列カードグリッドで表示
  各カード: 銘柄名 / パターン / 発表日時 / 5分足エリアチャート + 発表時刻縦線

ローカル前提: C:\\stock_analysis\\data\\prices\\stocks\\{5min,daily}\\{code}.parquet
（yfinance 5分足は約60日上限のため、ローカル保存データを使う）

決算日時の取得方法は連載07 の TDnet パイプライン参照。

起動: streamlit run app3.py
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.paths import rakunav_file
from utils.master_names import apply_master_names

PRICES_5MIN  = Path(r"C:\stock_analysis\data\prices\stocks\5min")
PRICES_DAILY = Path(r"C:\stock_analysis\data\prices\stocks\daily")
EARNINGS_CSV = Path(__file__).parent / "earnings.csv"


# ── ページ設定 + Wide / Narrow トグル ──────────────────────
st.set_page_config(page_title="決算パターングリッド", page_icon="📈", layout="wide")

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


# ── パラメータ ──────────────────────────────────────────────
DAYS_BEFORE = 1   # チャート 発表前 営業日数
DAYS_AFTER  = 3   # チャート 発表後 営業日数
RET_DAYS    = 5   # 最終リターン: 発表後初日 +N営業日
TH_FIRST    = 2.0 # 初日リターン flat 閾値（%）
TH_FINAL    = 3.0 # 最終リターン flat 閾値（%）

# SNS 5パターン分類: (初日, 最終) → ラベル
SNS_LABEL = {
    ("up",   "up"):   "🟢上げ📈", ("up",   "flat"): "逆V字",   ("up",   "down"): "逆V字",
    ("flat", "up"):   "無風",      ("flat", "flat"): "無風",     ("flat", "down"): "無風",
    ("down", "up"):   "V字",       ("down", "flat"): "🔴下げ💀", ("down", "down"): "🔴下げ💀",
}
SNS_ORDER = ["🟢上げ📈", "逆V字", "無風", "V字", "🔴下げ💀"]
SNS_DESC = {
    "🟢上げ📈": "初日も最終も上昇、決算好感が続く",
    "逆V字":    "初日↑から失速・反落",
    "無風":     "初日反応薄、スルー",
    "V字":      "初日↓から反発",
    "🔴下げ💀": "初日も最終も下落、悪材料継続",
}


# ── データ読込 ──────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_earnings() -> pd.DataFrame:
    df = pd.read_csv(EARNINGS_CSV, dtype={"code": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_5min(code: str) -> pd.DataFrame:
    p = PRICES_5MIN / f"{code}.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p).dropna(subset=["Close"]).reset_index()
    first = df.columns[0]
    if first != "Datetime":
        df = df.rename(columns={first: "Datetime"})
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    if df["Datetime"].dt.tz is None:
        df["Datetime"] = df["Datetime"].dt.tz_localize("Asia/Tokyo")
    else:
        df["Datetime"] = df["Datetime"].dt.tz_convert("Asia/Tokyo")
    df["_date"] = df["Datetime"].dt.date
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_daily(code: str) -> pd.DataFrame:
    p = PRICES_DAILY / f"{code}.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p).dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index).date
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_name_dict() -> dict[str, str]:
    """rakunav CSV + apply_master_names から {コード: 短縮銘柄名} を作る（app2 と同じ）。"""
    p = rakunav_file(113)  # 113: EPS実績 ― 銘柄名・コード列を含む任意の rakunav ファイル
    if p is None:
        return {}
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
    df["コード"] = df["コード"].astype(str).str.strip()
    df = apply_master_names(df)
    return dict(zip(df["コード"], df["銘柄名"].astype(str)))


def get_name(code: str, name_dict: dict[str, str]) -> str:
    return name_dict.get(code, f"{code}.T")


# ── パターン分類 ────────────────────────────────────────────
def _trend(pct: float | None, th: float) -> str | None:
    if pct is None or pd.isna(pct):
        return None
    if pct > th:  return "up"
    if pct < -th: return "down"
    return "flat"


def _is_after_close(t: str | None) -> bool:
    if not t: return True
    try:
        return int(t.split(":")[0]) >= 15
    except Exception:
        return True


def calc_returns(ann_date: date, ann_time: str | None,
                 df_daily: pd.DataFrame) -> tuple[float, float] | None:
    """初日リターン・最終リターン(%) を返す。"""
    if df_daily.empty:
        return None
    if _is_after_close(ann_time):
        # 引け後発表: pre=発表当日 Close, post=翌営業日 Close
        on = df_daily[df_daily.index <= ann_date]
        if on.empty: return None
        pre = float(on.iloc[-1]["Close"])
        nxt = df_daily[df_daily.index > on.index[-1]]
    else:
        # 場中/寄り前発表: pre=前営業日 Close, post=発表当日 Close
        before = df_daily[df_daily.index < ann_date]
        if before.empty: return None
        pre = float(before.iloc[-1]["Close"])
        nxt = df_daily[df_daily.index >= ann_date]
    if nxt.empty or pre == 0: return None
    post = float(nxt.iloc[0]["Close"])
    first_pct = (post - pre) / pre * 100
    after = df_daily[df_daily.index > nxt.index[0]].head(RET_DAYS)
    if after.empty or post == 0: return None
    final_pct = (float(after.iloc[-1]["Close"]) - post) / post * 100
    return first_pct, final_pct


def classify_sns(first_pct: float, final_pct: float) -> str | None:
    f, fn = _trend(first_pct, TH_FIRST), _trend(final_pct, TH_FINAL)
    if f is None or fn is None:
        return None
    return SNS_LABEL[(f, fn)]


# ── エリアチャート ────────────────────────────────────────
_N_BANDS = 6


def render_area_chart(df5: pd.DataFrame, ann_dt: datetime, line_color: str,
                      base_rgb: tuple[int, int, int], height: int = 200) -> go.Figure:
    """5分足エリア + 下方向グラデーション塗り + 発表時刻縦点線。"""
    df = df5.copy().sort_values("Datetime").reset_index(drop=True)
    df["x_key"] = df["Datetime"].dt.strftime("%y/%m/%d %H:%M")

    y_arr = df["Close"].astype(float).tolist()
    y_min, y_max = min(y_arr), max(y_arr)
    y_pad = (y_max - y_min) * 0.08
    y_floor = y_min - y_pad

    fig = go.Figure()
    # 透明ベース
    fig.add_trace(go.Scatter(
        x=df["x_key"], y=[y_floor] * len(df), mode="lines",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    # グラデーション帯
    for b in range(1, _N_BANDS + 1):
        ratio = b / _N_BANDS
        band_y = [y_floor + (c - y_floor) * ratio for c in y_arr]
        alpha = 0.04 + ratio * 0.18
        fig.add_trace(go.Scatter(
            x=df["x_key"], y=band_y, mode="lines",
            line=dict(width=0, color="rgba(0,0,0,0)"),
            fill="tonexty",
            fillcolor=f"rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},{alpha:.3f})",
            showlegend=False, hoverinfo="skip",
        ))
    # 終値ライン
    fig.add_trace(go.Scatter(
        x=df["x_key"], y=df["Close"], mode="lines",
        line=dict(color=line_color, width=1.8),
        showlegend=False,
        hovertemplate="%{x}<br>¥%{y:,.0f}<extra></extra>",
    ))

    # 発表時刻の縦点線（最も近い 5分足の位置に）
    ann_ts = pd.Timestamp(ann_dt, tz="Asia/Tokyo")
    diffs = (df["Datetime"] - ann_ts).abs()
    vline_x = df.loc[diffs.idxmin(), "x_key"]
    fig.add_vline(x=vline_x, line=dict(width=1.2, color=line_color, dash="dot"))

    # 日付境界の縦線（薄い灰）
    am_mask = df["Datetime"] == df.groupby("_date")["Datetime"].transform("min")
    for k in df[am_mask]["x_key"]:
        if k != vline_x:
            fig.add_vline(x=k, line=dict(width=1.0, color="#dddddd"))

    # X軸: 日付ラベル（各日の朝寄り位置）
    tickvals = df[am_mask]["x_key"].tolist()
    ticktext = [f"{d.month}/{d.day}" for d in df[am_mask]["_date"]]
    fig.update_xaxes(
        type="category", tickmode="array",
        tickvals=tickvals, ticktext=ticktext,
        tickfont=dict(size=14, color="#888"),
        showgrid=False, rangeslider_visible=False,
        showline=True, linecolor="#cccccc", linewidth=1,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#eeeeee", gridwidth=1,
        tickfont=dict(size=14, color="#888"),
        zeroline=False, side="right",
        tickformat=",d", showline=True, linecolor="#cccccc", linewidth=1,
        nticks=3, range=[y_floor, y_max + y_pad],
    )
    fig.update_layout(
        height=height,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=4, r=4, t=4, b=4),
        showlegend=False,
    )
    return fig


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("## 決算パターン<br>グリッド", unsafe_allow_html=True)
raw_codes = st.sidebar.text_area(
    "銘柄コード", value="5020\n6758\n7203\n7974\n8306\n9984\n8001\n8002\n8031\n8053\n8058\n2768",
    height=200,
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]
COLS_PER_ROW = 4
st.sidebar.caption(f"発表日時は同梱の `{EARNINGS_CSV.name}` から読み込みます")
st.sidebar.caption(
    f"発表後の値動きを **5パターン** に分類。"
    f"初日リターン: 発表前 Close → 発表後初日 Close（引け後発表は当日→翌営業日）／"
    f"最終リターン: 発表後初日 Close → +{RET_DAYS}営業日。"
    f"|初日|≤{TH_FIRST}% / |最終|≤{TH_FINAL}% は flat。"
)


# ── メイン: 集計 ──────────────────────────────────────────

try:
    earnings = load_earnings()
except Exception as e:
    st.error(f"earnings.csv 読み込みに失敗: {e}")
    st.stop()

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

# 入力銘柄に絞ったうえで分類
name_dict = load_name_dict()
rows: list[dict] = []
for _, e in earnings[earnings["code"].isin(tickers)].iterrows():
    code = e["code"]
    df_daily = load_daily(code)
    if df_daily.empty:
        continue
    ret = calc_returns(e["date"], e["time"], df_daily)
    if ret is None:
        continue
    first_pct, final_pct = ret
    pattern = classify_sns(first_pct, final_pct)
    if pattern is None:
        continue
    rows.append({
        "code": code, "name": get_name(code, name_dict),
        "date": e["date"], "time": e["time"],
        "first": first_pct, "final": final_pct, "pattern": pattern,
    })

if not rows:
    st.warning("分類可能な発表がありません")
    st.stop()

df_cls = pd.DataFrame(rows)
total = len(df_cls)


# ── 全銘柄のカードグリッド ──────────────────────────────
df_sel = df_cls.sort_values("date", ascending=False).reset_index(drop=True)


def render_card(r: pd.Series) -> None:
    df5_all = load_5min(r["code"])
    if df5_all.empty:
        st.caption(f"{r['code']}: 5分足データなし")
        return
    w_start = r["date"] - timedelta(days=DAYS_BEFORE + 3)
    w_end   = r["date"] + timedelta(days=DAYS_AFTER + 3)
    df5 = df5_all[(df5_all["_date"] >= w_start) & (df5_all["_date"] <= w_end)]
    if df5.empty:
        st.caption(f"{r['code']}: 期間内 5分足なし")
        return

    # チャート色は混乱を避けてグレー固定（パターンはラベルで表示）
    line_color, base_rgb = "#888888", (136, 136, 136)

    ann_dt = datetime.combine(r["date"], time(*map(int, r["time"].split(":"))))

    # 銘柄名 + コード
    st.markdown(
        f"<div style='line-height:1.3;margin-bottom:2px'>"
        f"<span style='font-weight:700;font-size:1.2em;color:#202124'>{r['name']}</span>"
        f"<span style='color:#70757a;font-size:0.8em'>　{r['code']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    # パターンラベル
    st.markdown(
        f"<div style='font-size:16px;color:#555;line-height:1.4;margin-bottom:2px'>"
        f"{r['pattern']}</div>",
        unsafe_allow_html=True,
    )
    # 発表日時
    st.markdown(
        f"<div style='font-size:12px;color:#888;line-height:1.4;margin-bottom:4px'>"
        f"{r['date'].month}月{r['date'].day}日 {r['time']}</div>",
        unsafe_allow_html=True,
    )
    # チャート
    fig = render_area_chart(df5, ann_dt, line_color, base_rgb)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


for i in range(0, len(df_sel), COLS_PER_ROW):
    chunk = df_sel.iloc[i: i + COLS_PER_ROW]
    cols = st.columns(COLS_PER_ROW, gap="medium")
    for j, col in enumerate(cols):
        if j >= len(chunk):
            continue
        with col:
            render_card(chunk.iloc[j])


# ── 全銘柄一覧 ───────────────────────────────────────────
with st.expander("📋 全銘柄一覧", expanded=False):
    show = df_cls[["code", "name", "date", "time", "first", "final", "pattern"]].copy()
    show.columns = ["コード", "銘柄名", "発表日", "発表時刻", "初日%", "最終%", "パターン"]
    show["初日%"] = show["初日%"].map("{:+.2f}".format)
    show["最終%"] = show["最終%"].map("{:+.2f}".format)
    st.dataframe(show, use_container_width=True, hide_index=True)
