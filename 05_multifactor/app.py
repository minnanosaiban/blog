"""
連載02: マルチファクター・スコアボード ― 7 ファクター（Value/Quality/Growth/Consensus/Sentiment/Momentum/Risk）
レーダーチャートで銘柄性格を可視化（Streamlit + Plotly）

ローカル前提: C:\\stock_analysis 配下の rakunav CSV + yfinance 日足 parquet を読みに行く。
データは利用規約により再配布しないため、各自の環境でセットアップしてください。

起動: streamlit run app.py
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from config.paths import rakunav_file
from utils.master_names import apply_master_names
from utils.price_metrics import compute_price_metrics
from utils.universe_topix500 import filter_to_topix500


# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="マルチファクター・スコアボード",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── ファクター定義 ─────────────────────────────────────────
# (内部カラム名, 高いほど良いか)
FACTOR_DEFS: dict[str, list[tuple[str, bool]]] = {
    "Value":     [("PER", False), ("PBR", False), ("EV/EBITDA", False), ("配当利回り", True)],
    "Quality":   [("ROE", True), ("ROA", True), ("営業利益率", True), ("自己資本比率", True)],
    "Growth":    [("売上高変化率", True), ("経常利益変化率", True)],
    "Consensus": [("業績予想修正率(予)", True), ("経常利益変化率(予)", True), ("過去3年平均売上高成長率(予)", True)],
    "Sentiment": [("出来高増加率", True), ("売買代金増加率", True)],
    "Momentum":  [("値上り率", True), ("過去52週安値からの上昇率", True), ("株価移動平均線からの乖離率①", True)],
    "Risk":      [("過去60日ボラティリティ", False), ("ベータ(対日経平均)", False)],
}

FACTOR_COLORS = {
    "Value":     "#4C8BF5",
    "Quality":   "#50C878",
    "Growth":    "#F5A623",
    "Consensus": "#9B59B6",
    "Sentiment": "#E05C5C",
    "Momentum":  "#1ABC9C",
    "Risk":      "#8C8C8C",
}

FACTORS = list(FACTOR_DEFS.keys())


# ── データ取得 ──────────────────────────────────────────────
RAKUNAV_SPECS = [
    (113, "EPS実績",   "EPS(一株あたり当期利益)"),
    (215, "BPS予",     "BPS(予)(一株あたり純資産)"),
    (141, "配当金",     "配当金(円)"),
    (133, "EV/EBITDA", "EV/EBITDA倍率"),
    (118, "ROE",       "ROE(自己資本利益率)"),
    (119, "ROA",       "ROA(総資産当期利益率)"),
    (125, "営業利益率", "売上高営業利益率"),
    (130, "自己資本比率", "自己資本比率"),
    (122, "売上高変化率",   "売上高変化率"),
    (129, "経常利益変化率", "経常利益変化率"),
    (219, "過去3年平均売上高成長率(予)", "過去3年平均売上高成長率(予)"),
    (220, "業績予想修正率(予)", "業績予想修正率(予)"),
    (221, "経常利益変化率(予)", "経常利益変化率(予)"),
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


def _to_float_price(s):
    return _to_float(s)


@st.cache_data(ttl=3600, show_spinner="📥 楽天 MS2 CSV を読み込んでいます…")
def load_rakunav() -> pd.DataFrame:
    """rakunav 14 指標 + 現在値を merge した TOPIX 500 ベースのユニバース。"""
    merged = None
    price_series = None
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
        if price_series is None and "現在値" in df.columns:
            price_series = df.set_index("コード")["現在値"].map(_to_float_price)
        d = df[["コード", "銘柄名", "市場", label]]
        merged = d if merged is None else merged.merge(
            d, on=["コード", "銘柄名", "市場"], how="outer"
        )

    merged["現在値"] = merged["コード"].map(price_series)
    # Value 派生
    merged["PER"] = merged["現在値"] / merged["EPS実績"].where(merged["EPS実績"] > 0)
    merged["PBR"] = merged["現在値"] / merged["BPS予"].where(merged["BPS予"] > 0)
    merged["配当利回り"] = (merged["配当金"] / merged["現在値"].where(merged["現在値"] > 0)) * 100

    merged = filter_to_topix500(merged)
    merged = apply_master_names(merged)
    return merged.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner="📈 TOPIX 500 の価格メトリクスを計算中（30秒程度）…")
def load_price_metrics(codes_tuple: tuple[str, ...]) -> pd.DataFrame:
    return compute_price_metrics(list(codes_tuple))


def _percentile(series: pd.Series, higher_better: bool) -> pd.Series:
    ranked = series.rank(pct=True, na_option="keep") * 100
    if not higher_better:
        ranked = 100 - ranked
    return ranked


def compute_factor_scores(df: pd.DataFrame) -> pd.DataFrame:
    """各指標を universe 全体でパーセンタイル化し、ファクター毎に平均。総合スコアも追加。"""
    out = df.copy()
    for factor, indicators in FACTOR_DEFS.items():
        cols = []
        for col, higher_better in indicators:
            if col in out.columns:
                out[f"_p_{col}"] = _percentile(out[col], higher_better)
                cols.append(f"_p_{col}")
        if cols:
            out[factor] = out[cols].mean(axis=1)
    out["総合スコア"] = out[FACTORS].mean(axis=1)
    # 内部列を削除
    out = out.drop(columns=[c for c in out.columns if c.startswith("_p_")])
    return out


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# マルチファクター<br>スコアボード", unsafe_allow_html=True)

raw_codes = st.sidebar.text_area(
    "銘柄コード",
    value="5020\n5021\n5019\n3105\n8750\n1605",
    height=240,
    help="カンマ・改行・スペースで区切れます。3 列カードグリッドで表示します",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]


# ── データロード ──────────────────────────────────────────────
try:
    df_rk = load_rakunav()
except Exception as e:
    st.error(f"rakunav 読み込みに失敗: {e}")
    st.stop()

try:
    pm = load_price_metrics(tuple(df_rk["コード"].tolist()))
except Exception as e:
    st.error(f"価格メトリクス計算に失敗: {e}")
    st.stop()

df_all = df_rk.merge(pm, on="コード", how="left")
df_all = compute_factor_scores(df_all)


# 入力コードでフィルタ
df = df_all[df_all["コード"].isin(tickers)].copy()
missing = [t for t in tickers if t not in df_all["コード"].values]


# ── メイン ──────────────────────────────────────────────
st.markdown("**⬛マルチファクター・スコアボード**")
st.caption(" TOPIX 500 内で7 ファクターを相対評価。総合スコア 70 以上が上位 30% の注目候補。")

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

if missing:
    st.warning(f"見つからなかった銘柄コード（TOPIX 500 外含む）: {', '.join(missing)}")

if df.empty:
    st.error("有効な銘柄が見つかりませんでした（TOPIX 500 内の銘柄のみ表示できます）")
    st.stop()

# 入力順にソート
df["_order"] = df["コード"].map({c: i for i, c in enumerate(tickers)})
df = df.sort_values("_order").drop(columns="_order").reset_index(drop=True)


# ── レーダーチャートカードグリッド（3 列）──────────────────
def _radar_fig(row: pd.Series) -> go.Figure:
    values = [row.get(f, 0) if pd.notna(row.get(f)) else 0 for f in FACTORS]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # 閉じる
        theta=FACTORS + [FACTORS[0]],
        fill="toself",
        line=dict(color="#3498db", width=2),
        fillcolor="rgba(52, 152, 219, 0.25)",
        showlegend=False,
        hoverinfo="text",
        text=[f"{f}: {v:.1f}" for f, v in zip(FACTORS, values)] + [f"{FACTORS[0]}: {values[0]:.1f}"],
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=True,
                            tickvals=[25, 50, 75], tickfont=dict(size=8, color="#999"),
                            ticks="", gridcolor="rgba(0,0,0,0.06)",
                            showline=False),
            angularaxis=dict(tickfont=dict(size=9, color="#202124"),
                             gridcolor="rgba(0,0,0,0.06)",
                             linecolor="rgba(0,0,0,0.15)"),
            bgcolor="white",
        ),
        height=220,
        margin=dict(t=30, b=30, l=0, r=0),
        showlegend=False,
        paper_bgcolor="white",
    )
    return fig


COLS_PER_ROW = 3
records = df.to_dict("records")

# 列間ギャップを CSS で詰める（複数レーダー俯瞰のため）
st.markdown(
    """
    <style>
    [data-testid="stHorizontalBlock"] { gap: 0.25rem !important; }
    [data-testid="column"] { padding: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

for i in range(0, len(records), COLS_PER_ROW):
    chunk = records[i:i + COLS_PER_ROW]
    cols = st.columns(COLS_PER_ROW, gap="small")
    for j, col in enumerate(cols):
        if j >= len(chunk):
            with col:
                st.empty()
            continue
        r = chunk[j]
        with col:
            name = r["銘柄名"]
            code = r["コード"]
            total = r.get("総合スコア", float("nan"))
            total_str = f"{total:.1f}" if pd.notna(total) else "—"
            total_color = "#27ae60" if pd.notna(total) and total >= 70 else "#3498db" if pd.notna(total) and total >= 50 else "#e74c3c"
            hdr = (
                f"<div style='text-align:center;line-height:1.3;margin-bottom:0px'>"
                f"<span style='font-weight:700;font-size:1.0em;color:#202124'>{name}</span>"
                f"<span style='color:#70757a;font-size:0.8em'>（{code}）</span>"
                f"<span style='font-weight:700;color:{total_color};font-size:0.9em'>　総合 {total_str}</span>"
                f"</div>"
            )
            st.markdown(hdr, unsafe_allow_html=True)
            st.plotly_chart(_radar_fig(pd.Series(r)), use_container_width=True, config={"displayModeBar": False})


# ── 詳細テーブル ──────────────────────────────────────────────
st.markdown("**⬛ファクタースコア一覧**")
detail = df[["コード", "銘柄名"] + FACTORS + ["総合スコア"]].copy()
fmt = {f: lambda x: f"{x:.1f}" if pd.notna(x) else "—" for f in FACTORS + ["総合スコア"]}
st.dataframe(
    detail.style.format(fmt),
    use_container_width=True,
    hide_index=True,
)
