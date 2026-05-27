"""
連載04: 連続サプライズ・スコアボード ― 業績予想修正率 × 経常利益変化率(予) 4 象限マトリクス（Streamlit + Plotly）

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
    page_title="連続サプライズ・スコアボード",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ── データ取得 ──────────────────────────────────────────────
RAKUNAV_SPECS = [
    (220, "業績予想修正率(予)", "業績予想修正率(予)"),
    (213, "EPS予",   "EPS(予)(一株あたり当期利益)"),
    (113, "EPS実績", "EPS(一株あたり当期利益)"),
    (221, "経常利益変化率(予)", "経常利益変化率(予)"),
    (118, "ROE",    "ROE(自己資本利益率)"),
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


def _percentile(series: pd.Series, higher_better: bool = True) -> pd.Series:
    ranked = series.rank(pct=True, na_option="keep") * 100
    if not higher_better:
        ranked = 100 - ranked
    return ranked


@st.cache_data(ttl=3600, show_spinner="📥 楽天 MS2 CSV を読み込んでいます…")
def load_universe() -> pd.DataFrame:
    """rakunav 6 指標を merge + EPS超過率・サプライズスコア を計算した銘柄ユニバース。"""
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

    # EPS予想超過率 = (EPS予 − EPS実) / |EPS実| × 100  （EPS実 絶対値 1 円未満は欠損扱い）
    safe_actual = merged["EPS実績"].where(merged["EPS実績"].abs() >= 1.0)
    merged["EPS予想超過率"] = ((merged["EPS予"] - safe_actual) / safe_actual.abs()) * 100

    # サプライズスコア = 修正率・EPS超過率・経常変化率(予) のパーセンタイル平均
    merged["_s_rev"] = _percentile(merged["業績予想修正率(予)"], higher_better=True)
    merged["_s_eps"] = _percentile(merged["EPS予想超過率"], higher_better=True)
    merged["_s_ord"] = _percentile(merged["経常利益変化率(予)"], higher_better=True)
    merged["サプライズスコア"] = merged[["_s_rev", "_s_eps", "_s_ord"]].mean(axis=1)
    merged = merged.drop(columns=["_s_rev", "_s_eps", "_s_ord"])

    merged = apply_master_names(merged)
    return merged


def classify_surprise(df: pd.DataFrame, rev_th: float) -> pd.Series:
    """業績予想修正率 × 経常利益変化率(予) の 4 象限分類（右上=本命）。"""
    zone = pd.Series("中立", index=df.index)
    up_rev = df["業績予想修正率(予)"] >= rev_th
    dn_rev = df["業績予想修正率(予)"] <= -rev_th
    growth = df["経常利益変化率(予)"] > 0
    decline = df["経常利益変化率(予)"] <= 0

    zone[up_rev & growth]  = "🌟 上方修正 × 来期成長"
    zone[dn_rev & growth]  = "🔄 回復期待"
    zone[dn_rev & decline] = "🚫 回避ゾーン"
    zone[up_rev & decline] = "📉 ピークアウト警戒"
    return zone


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# 連続サプライズ<br>スコアボード", unsafe_allow_html=True)

raw_codes = st.sidebar.text_area(
    "銘柄コード",
    value="3105\n4478\n3176\n8750\n6588\n7270\n3350\n3994\n6875\n1605",
    height=240,
    help="カンマ・改行・スペースで区切れます",
)
tickers = [t.strip() for t in re.split(r"[,\s\n]+", raw_codes) if t.strip()]

# しきい値（連載04 記事と統一）
REV_TH = 3.0   # 業績予想修正率 ±3%


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
st.markdown("**⬛業績予想修正率 × 経常利益変化率(予想) 4 象限マトリクス**")
st.caption(f" 修正率 ±{REV_TH:g}% / 経常変化率 0% 境界 で 4 象限を分類")

if not tickers:
    st.info("👈 サイドバーに銘柄コードを入力してください")
    st.stop()

if missing:
    st.warning(f"見つからなかった銘柄コード: {', '.join(missing)}")

if df.empty:
    st.error("有効な銘柄が見つかりませんでした")
    st.stop()

df_plot = df.dropna(subset=["業績予想修正率(予)", "経常利益変化率(予)"]).copy()

# 経常利益変化率(予) 欠損銘柄の警告（記事でも「コスモエネＨＤ 経常データ欠損」等が頻出）
missing_ord = df[df["経常利益変化率(予)"].isna()]
if not missing_ord.empty:
    labels = [f"{r['コード']} {r['銘柄名']}" for _, r in missing_ord.iterrows()]
    st.warning(f"⚠️ 経常利益変化率(予想) が欠損のため散布図対象外（テーブルには掲載）: {' / '.join(labels)}")

if df_plot.empty:
    st.error("プロット対象の銘柄がありません（修正率・経常変化率が両方ある銘柄のみ表示できます）")
else:
    df_plot["分類"] = classify_surprise(df_plot, REV_TH)


# ── 散布図 ──────────────────────────────────────────────
COLOR_MAP = {
    "🌟 上方修正 × 来期成長": "#27ae60",
    "🔄 回復期待": "#3498db",
    "🚫 回避ゾーン": "#e74c3c",
    "📉 ピークアウト警戒": "#e67e22",
    "中立": "#888888",
}

XLIM = (-50.0, 50.0)
YLIM = (-50.0, 50.0)

df_plot["修正率_表示"] = df_plot["業績予想修正率(予)"].clip(lower=XLIM[0] + 0.3, upper=XLIM[1] - 0.3)
df_plot["経常変化_表示"] = df_plot["経常利益変化率(予)"].clip(lower=YLIM[0] + 1, upper=YLIM[1] - 1)
df_plot["ラベル"] = df_plot["コード"]

fig = px.scatter(
    df_plot,
    x="修正率_表示",
    y="経常変化_表示",
    color="分類",
    color_discrete_map=COLOR_MAP,
    text="ラベル",
    labels={
        "業績予想修正率(予)": "業績予想修正率(予想)",
        "経常利益変化率(予)": "経常利益変化率(予想)",
    },
    hover_data={
        "コード": True,
        "銘柄名": True,
        "業績予想修正率(予)": ":+.2f",
        "経常利益変化率(予)": ":+.2f",
        "EPS予想超過率": ":+.2f",
        "サプライズスコア": ":.1f",
        "ROE": ":.1f",
        "時価総額": ":,.0f",
        "修正率_表示": False,
        "経常変化_表示": False,
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
    tickvals=[-50, -30, -10, -3, 0, 3, 10, 30, 50],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)
fig.update_yaxes(
    title="経常利益変化率(予想)(%) ← 来期減益　来期成長 →",
    range=list(YLIM),
    tickvals=[-50, -30, -10, 0, 10, 30, 50],
    showgrid=True, gridcolor="rgba(0,0,0,0.06)",
)

# 4 象限を薄い背景色で識別（右上=本命）
ZONE_FILL = [
    # (x0, x1, y0, y1, fillcolor)
    (REV_TH,  XLIM[1], 0,       YLIM[1], "rgba(39, 174, 96, 0.10)"),    # 右上: 上方修正×来期成長
    (XLIM[0], -REV_TH, 0,       YLIM[1], "rgba(52, 152, 219, 0.08)"),   # 左上: 回復期待
    (XLIM[0], -REV_TH, YLIM[0], 0,       "rgba(231, 76, 60, 0.08)"),    # 左下: 回避ゾーン
    (REV_TH,  XLIM[1], YLIM[0], 0,       "rgba(230, 126, 34, 0.08)"),   # 右下: ピークアウト警戒
]
for x0, x1, y0, y1, color in ZONE_FILL:
    fig.add_shape(
        type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
        fillcolor=color, line=dict(width=0), layer="below",
    )
fig.add_vline(x=REV_TH,  line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)
fig.add_vline(x=-REV_TH, line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)
fig.add_hline(y=0,       line_dash="dash", line_color="rgba(0,0,0,0.3)", line_width=0.8)

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
🟩 緑　上方修正 × 来期成長<br>
🟦 青　回復期待<br>
🟥 赤　回避ゾーン<br>
🟧 橙　ピークアウト警戒<br>
⬜ 灰　中立
""",
        unsafe_allow_html=True,
    )


# ── 詳細テーブル ──────────────────────────────────────────────
st.markdown("**⬛銘柄一覧**（散布図対象外の経常変化率欠損銘柄もここに掲載）")
# df_plot で計算した分類を full df に left-merge（欠損銘柄は分類=「— (経常欠損)」と表示）
df_table = df.merge(
    df_plot[["コード", "分類"]] if "分類" in df_plot.columns else pd.DataFrame(columns=["コード", "分類"]),
    on="コード", how="left",
)
df_table["分類"] = df_table["分類"].fillna("— (経常欠損)")
detail = df_table[[
    "コード", "銘柄名", "業績予想修正率(予)", "経常利益変化率(予)",
    "EPS予想超過率", "サプライズスコア", "ROE", "時価総額", "分類",
]].rename(columns={
    "業績予想修正率(予)": "業績予想修正率(予想)",
    "経常利益変化率(予)": "経常利益変化率(予想)",
}).copy()
st.dataframe(
    detail.style.format({
        "業績予想修正率(予想)": lambda x: f"{x:+.2f}%" if pd.notna(x) else "—",
        "経常利益変化率(予想)": lambda x: f"{x:+.2f}%" if pd.notna(x) else "—",
        "EPS予想超過率": lambda x: f"{x:+.2f}%" if pd.notna(x) else "—",
        "サプライズスコア": lambda x: f"{x:.1f}" if pd.notna(x) else "—",
        "ROE": lambda x: f"{x:.1f}%" if pd.notna(x) else "—",
        "時価総額": lambda x: f"{x:,.0f}" if pd.notna(x) else "—",
    }),
    use_container_width=True,
    hide_index=True,
)
