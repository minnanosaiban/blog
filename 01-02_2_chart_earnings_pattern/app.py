"""
03_earnings_pattern/app.py — 決算パターングリッド（5分足エリアチャート）

- 同梱の earnings.csv（date,time,code）から発表銘柄を集計
- 発表後の値動きを 5 パターンに分類（上げ / 逆V字 / 無風 / V字 / 下げ）
- 選択銘柄を 4列カードグリッドで表示
  各カード: 銘柄名 / パターン / 発表日時 / 5分足エリアチャート + 発表時刻縦線
- データ: data/prices/{5min,daily}/{code}.parquet

起動: streamlit run 03_earnings_pattern/app.py
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR     = Path(__file__).parent / "data"
PRICES_5MIN  = DATA_DIR / "prices" / "5min"
PRICES_DAILY = DATA_DIR / "prices" / "daily"
EARNINGS_CSV = Path(__file__).parent / "earnings.csv"
COLS_PER_ROW = 4


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(page_title="5分足チャート_決算確認", page_icon="📈", layout="wide")

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


# ── パラメータ ──────────────────────────────────────────────
DAYS_BEFORE = 1
DAYS_AFTER  = 3
RET_DAYS    = DAYS_AFTER
TH_FIRST    = 2.0
TH_FINAL    = 3.0

SNS_LABEL = {
    ("up",   "up"):   "🟢上げ", ("up",   "flat"): "逆V字",   ("up",   "down"): "逆V字",
    ("flat", "up"):   "無風",      ("flat", "flat"): "無風",     ("flat", "down"): "無風",
    ("down", "up"):   "V字",       ("down", "flat"): "🔴下げ", ("down", "down"): "🔴下げ",
}
SNS_ORDER = ["🟢上げ", "逆V字", "無風", "V字", "🔴下げ"]


# ── マスタ・銘柄名 ──────────────────────────────────────────
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
def get_name(code: str) -> str:
    master = _load_master()
    if master.empty:
        return code
    row = master[master["コード"] == str(code)]
    if row.empty:
        return code
    r = row.iloc[0]
    for col in ("銘柄", "銘柄名"):
        val = r.get(col, None)
        if pd.notna(val) and val:
            return str(val)
    return code


@st.cache_data(ttl=3600, show_spinner=False)
def load_topix500_codes() -> list[str]:
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
    return sorted(
        master[master[col_size].isin(targets)][col_code]
        .dropna().astype(str).str.strip().tolist()
    )


# ── データ読込 ──────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_earnings() -> pd.DataFrame:
    df = pd.read_csv(EARNINGS_CSV, dtype={"code": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
def load_daily(code: str) -> pd.DataFrame:
    p = PRICES_DAILY / f"{code}.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p).dropna(subset=["Close"])
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).date
    return df.sort_index()


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
    if df_daily.empty:
        return None
    if _is_after_close(ann_time):
        on = df_daily[df_daily.index <= ann_date]
        if on.empty: return None
        pre = float(on.iloc[-1]["Close"])
        nxt = df_daily[df_daily.index > on.index[-1]]
    else:
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


# ── エリアチャート ──────────────────────────────────────────
_N_BANDS = 6


def render_area_chart(df5: pd.DataFrame, ann_dt: datetime,
                      height: int = 200) -> go.Figure:
    df = df5.copy().sort_values("Datetime").reset_index(drop=True)
    df["x_key"] = df["Datetime"].dt.strftime("%y/%m/%d %H:%M")

    y_arr = df["Close"].astype(float).tolist()
    y_min, y_max = min(y_arr), max(y_arr)
    y_pad   = (y_max - y_min) * 0.08
    y_floor = y_min - y_pad

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["x_key"], y=[y_floor] * len(df), mode="lines",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    for b in range(1, _N_BANDS + 1):
        ratio = b / _N_BANDS
        alpha = 0.04 + ratio * 0.18
        fig.add_trace(go.Scatter(
            x=df["x_key"],
            y=[y_floor + (c - y_floor) * ratio for c in y_arr],
            mode="lines",
            line=dict(width=0, color="rgba(0,0,0,0)"),
            fill="tonexty",
            fillcolor=f"rgba(136,136,136,{alpha:.3f})",
            showlegend=False, hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=df["x_key"], y=df["Close"], mode="lines",
        line=dict(color="#888888", width=1.8),
        showlegend=False,
        hovertemplate="%{x}<br>¥%{y:,.0f}<extra></extra>",
    ))

    ann_ts  = pd.Timestamp(ann_dt, tz="Asia/Tokyo")
    diffs   = (df["Datetime"] - ann_ts).abs()
    vline_x = df.loc[diffs.idxmin(), "x_key"]
    fig.add_vline(x=vline_x, line=dict(width=2.0, color="#222222", dash="dot"))

    am_mask = df["Datetime"] == df.groupby("_date")["Datetime"].transform("min")
    for k in df[am_mask]["x_key"]:
        if k != vline_x:
            fig.add_vline(x=k, line=dict(width=1.0, color="#dddddd"))

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


# ── カード描画 ──────────────────────────────────────────────
def render_card(r: pd.Series) -> None:
    df5_all = load_5min(r["code"])
    if df5_all.empty:
        st.caption(f"{r['code']}: 5分足データなし")
        return

    all_dates = sorted(df5_all["_date"].unique())
    ann_idx   = next((i for i, d in enumerate(all_dates) if d >= r["date"]), None)
    if ann_idx is None:
        st.caption(f"{r['code']}: 期間内 5分足なし")
        return
    start_idx = max(0, ann_idx - DAYS_BEFORE)
    end_idx   = min(len(all_dates) - 1, ann_idx + DAYS_AFTER)
    df5 = df5_all[df5_all["_date"].isin(set(all_dates[start_idx: end_idx + 1]))]
    if df5.empty:
        st.caption(f"{r['code']}: 期間内 5分足なし")
        return

    raw_time = r["time"]
    if pd.isna(raw_time) or not str(raw_time).strip():
        ann_dt = datetime.combine(r["date"], time(15, 30))
    else:
        ann_dt = datetime.combine(r["date"], time(*map(int, str(raw_time).split(":"))))

    st.markdown(
        f"<div style='line-height:1.3;margin-bottom:2px'>"
        f"<span style='font-weight:700;font-size:1.2em;color:#202124'>{r['name']}</span>"
        f"<span style='color:#70757a;font-size:0.8em'>　{r['code']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:16px;color:#555;line-height:1.4;margin-bottom:2px'>"
        f"{r['pattern']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:12px;color:#888;line-height:1.4;margin-bottom:4px'>"
        f"{r['date'].month}月{r['date'].day}日 {r['time']}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(render_area_chart(df5, ann_dt),
                    use_container_width=True, config={"displayModeBar": False})


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.checkbox("Wide 表示", key="_wide_layout")
st.sidebar.markdown("# 5分足チャート<br>決算確認", unsafe_allow_html=True)
today_obj = datetime.now()
today_str = f"{today_obj.year}年{today_obj.month}月{today_obj.day}日"
st.sidebar.caption(today_str)
st.sidebar.divider()

# ── チャート表示 ────────────────────────────────────────────
st.sidebar.markdown("### ⬛ チャート表示")

raw_codes = st.sidebar.text_area(
    "銘柄コード（改行 / スペース / カンマ区切り）",
    value="5020\n6758\n7203\n7974\n8306\n9984\n8001\n8031\n8058",
    height=160,
)
btn_show = st.sidebar.button("チャート表示", use_container_width=True)

st.sidebar.divider()

# ── データ取得 ──────────────────────────────────────────────
st.sidebar.markdown("### ⬛ データ取得")

with st.sidebar.expander("データ取得"):
    # ── 株価取得 ──────────────────────────────────────────
    st.markdown("**株価データ**")
    mode     = st.radio("銘柄選択", ["銘柄コード指定", "TOPIX500"],
                        horizontal=True, key="_data_mode")
    is_topix = mode == "TOPIX500"

    fetch_raw = st.text_area(
        "銘柄コード",
        value="5020\n6758\n7203",
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

    st.divider()

    # ── 決算日時取得 ────────────────────────────────────────
    st.markdown("**決算日時（earnings.csv）**")

    # TDnet 自動取得
    st.caption("TDnet から決算発表日時を自動取得します。")
    import datetime as _dt
    _col_s, _col_e = st.columns(2)
    with _col_s:
        tdnet_start = st.date_input("開始日",
                                    value=_dt.date.today().replace(day=1))
    with _col_e:
        tdnet_end = st.date_input("終了日",
                                  value=_dt.date.today())
    btn_tdnet = st.button("TDnet から取得", use_container_width=True)

    btn_build = False
    uploaded  = None

st.sidebar.divider()

# ── メイン ──────────────────────────────────────────────────
if btn_tdnet:
    try:
        _app_dir = str(Path(__file__).parent)
        if _app_dir not in sys.path:
            sys.path.insert(0, _app_dir)
        from fetch_tdnet import build_earnings, business_days
        _days = business_days(tdnet_start, tdnet_end)
        if not _days:
            st.warning("指定期間に営業日がありません。")
        else:
            bar = st.progress(0, text="TDnet を取得しています...")
            def _cb(i, total, d):
                bar.progress((i + 1) / total,
                             text=f"取得中 {i+1}/{total}: {d}")
            _df = build_earnings(tdnet_start, tdnet_end, progress_cb=_cb)
            bar.empty()
            if _df.empty:
                st.warning("決算短信の開示が見つかりませんでした。")
            else:
                _df.to_csv(EARNINGS_CSV, index=False, encoding="utf-8-sig")
                st.success(f"取得完了: {len(_df)} 件 → earnings.csv を更新しました")
                st.cache_data.clear()
    except Exception as e:
        st.error(f"取得に失敗しました: {e}")

elif btn_build and uploaded is not None:
    try:
        df_up = pd.read_csv(uploaded, dtype={"code": str})
        missing = [c for c in ["date", "time", "code"] if c not in df_up.columns]
        if missing:
            st.error(f"列が不足しています: {missing}　必要列: date, time, code")
        else:
            df_up["date"] = pd.to_datetime(df_up["date"]).dt.date
            df_up = (df_up.sort_values(["date", "code", "time"])
                         .drop_duplicates(subset=["date", "code"], keep="first")
                         .reset_index(drop=True))
            df_up.to_csv(EARNINGS_CSV, index=False, encoding="utf-8-sig")
            st.success(f"earnings.csv を保存しました（{len(df_up)} 件）")
            st.cache_data.clear()
    except Exception as e:
        st.error(f"保存に失敗しました: {e}")

elif btn_fetch:
    fetch_tickers = (
        t500_codes if is_topix
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
        st.stop()

    try:
        earnings = load_earnings()
    except Exception as e:
        st.error(f"earnings.csv 読み込みに失敗: {e}")
        st.stop()

    rows: list[dict] = []
    for _, e in earnings[earnings["code"].isin(chart_tickers)].iterrows():
        code     = e["code"]
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
            "code": code, "name": get_name(code),
            "date": e["date"], "time": e["time"],
            "first": first_pct, "final": final_pct, "pattern": pattern,
        })

    if not rows:
        st.warning("分類可能な発表がありません（earnings.csv・価格データを確認してください）")
        st.stop()

    df_cls = pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)

    for i in range(0, len(df_cls), COLS_PER_ROW):
        chunk = df_cls.iloc[i: i + COLS_PER_ROW]
        cols  = st.columns(COLS_PER_ROW, gap="medium")
        for j, col in enumerate(cols):
            if j >= len(chunk):
                continue
            with col:
                render_card(chunk.iloc[j])

    with st.expander("📋 全銘柄一覧", expanded=False):
        show = df_cls[["code", "name", "date", "time", "first", "final", "pattern"]].copy()
        show.columns = ["コード", "銘柄名", "発表日", "発表時刻", "初日%", "最終%", "パターン"]
        show["初日%"] = show["初日%"].map("{:+.2f}".format)
        show["最終%"] = show["最終%"].map("{:+.2f}".format)
        st.dataframe(show, use_container_width=True, hide_index=True)

else:
    n_5min  = len(list(PRICES_5MIN.glob("*.parquet")))  if PRICES_5MIN.exists()  else 0
    n_daily = len(list(PRICES_DAILY.glob("*.parquet"))) if PRICES_DAILY.exists() else 0
    has_earnings = EARNINGS_CSV.exists() and EARNINGS_CSV.stat().st_size > 0

    st.markdown("### はじめに")

    # ── Step 1: 株価データ ──
    if n_daily == 0 or n_5min == 0:
        st.error(
            "**Step 1: 株価データを取得してください**  \n"
            "左サイドバー「⬛ データ取得」→「データ取得」を開き、"
            "銘柄コードを入力して **「株価を取得」** を押してください。  \n"
            f"現在: 日足 {n_daily} 銘柄 / 5分足 {n_5min} 銘柄"
        )
    else:
        st.success(f"✅ Step 1: 株価データあり（日足 {n_daily} 銘柄 / 5分足 {n_5min} 銘柄）")

    # ── Step 2: earnings.csv ──
    if not has_earnings:
        st.error("**Step 2: 決算発表日時を取得してください**")
        st.markdown(
            "左サイドバー「⬛ データ取得」→「データ取得」を開き、  \n"
            "**開始日・終了日を設定して「TDnet から取得」** を押してください。  \n\n"
            "> 💡 見たい決算期の発表月を含む日付レンジを指定してください。  \n"
            "> 例: 3月期決算（5月発表）→ 開始日 `2026-05-01`、終了日 `2026-05-31`"
        )
    else:
        try:
            _e = pd.read_csv(EARNINGS_CSV, dtype={"code": str})
            _e_dates = pd.to_datetime(_e["date"]).dt.date
            _date_range = f"{_e_dates.min()} 〜 {_e_dates.max()}" if not _e.empty else "―"
            st.success(
                f"✅ Step 2: earnings.csv あり（{len(_e)} 件 / {_date_range}）  \n"
                "古いデータを更新したい場合は「TDnet から取得」を再実行してください。"
            )
        except Exception:
            st.warning("⚠️ Step 2: earnings.csv の読み込みに失敗しました")

    # ── Step 3: チャート表示 ──
    if n_daily > 0 and n_5min > 0 and has_earnings:
        st.info("👈 銘柄コードを入力し「チャート表示」を押してください")
