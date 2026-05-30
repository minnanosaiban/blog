"""
連載03 7年業績チャート ― 有報 JSON から純利益（棒）+ ROE（線）の時系列を描く

- data/yuho/{EDINETコード}/*.json を読み込み、銘柄ごとの業績時系列を構築
- 銘柄を選ぶと、純利益（棒・黒字=緑/赤字=赤）と ROE（線・右軸）を重ねて表示
- 純利益ピークの年に注釈を付ける

起動: streamlit run app.py

※ 有報 JSON（決算データ）は提供元の規約により再配布できません。
   data/yuho/ は空のプレースホルダです。XBRL → JSON 変換で生成してください。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="7年業績チャート", page_icon="📊", layout="wide")

# Wide / Narrow トグル（既定は Narrow）
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

DATA = Path(__file__).resolve().parent / "data" / "yuho"

C_POS = "#7fae8e"   # 黒字（棒）
C_NEG = "#d39a9a"   # 赤字（棒）
C_ROE = "#6b7280"   # ROE（線）
C_PEAK = "#c0392b"  # ピーク注釈


@st.cache_data(show_spinner=False)
def scan_companies() -> dict:
    """EDINETコード -> 社名 の辞書を返す。"""
    out: dict[str, str] = {}
    if not DATA.exists():
        return out
    for d in sorted(DATA.iterdir()):
        if not d.is_dir():
            continue
        files = sorted(d.glob("*.json"))
        if not files:
            continue
        try:
            meta = json.load(open(files[-1], encoding="utf-8")).get("metadata", {})
            out[d.name] = meta.get("company_name") or d.name
        except Exception:
            out[d.name] = d.name
    return out


@st.cache_data(show_spinner=False)
def load_series(edinet: str) -> pd.DataFrame:
    """1社の有報 JSON から 年度・純利益・ROE の時系列を作る。"""
    rows = []
    for f in sorted((DATA / edinet).glob("*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        meta = d.get("metadata", {}) or {}
        fin = d.get("financials", {}) or {}
        fy = str(meta.get("fiscal_year_end", ""))[:4]
        if not fy:
            continue
        rows.append({"fy": fy,
                     "net_income": fin.get("net_income"),
                     "roe": fin.get("roe")})
    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
            .drop_duplicates("fy", keep="last")
            .sort_values("fy")
            .reset_index(drop=True))


def make_fig(df: pd.DataFrame, name: str) -> go.Figure:
    x = df["fy"]
    ni = df["net_income"].astype(float) / 1e11          # 千億円
    roe = df["roe"].astype(float) * 100                 # %

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=x, y=ni, name="純利益（千億円）",
        marker_color=[C_POS if (pd.notna(v) and v >= 0) else C_NEG for v in ni],
        text=[f"{v:.1f}" if pd.notna(v) else "" for v in ni], textposition="outside",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=roe, name="ROE（%）", mode="lines+markers+text",
        line=dict(color=C_ROE, width=2.5), marker=dict(size=8),
        text=[f"{v:.1f}%" if pd.notna(v) else "" for v in roe], textposition="top center",
        textfont=dict(color=C_ROE),
    ), secondary_y=True)

    # 純利益ピークに注釈
    if ni.notna().any():
        i = int(ni.idxmax())
        ni_oku = df["net_income"].iloc[i]
        peak = f"{x.iloc[i]} ピーク"
        if pd.notna(ni_oku):
            peak += f"<br>純利益 {ni_oku / 1e8:,.0f} 億円"
        if pd.notna(roe.iloc[i]):
            peak += f" / ROE {roe.iloc[i]:.1f}%"
        fig.add_annotation(
            x=x.iloc[i], y=ni.iloc[i], yref="y",
            text=peak, showarrow=True, arrowhead=2, arrowcolor=C_PEAK,
            font=dict(color=C_PEAK), ax=0, ay=-55,
        )

    fig.update_layout(
        title=dict(text=f"{name} ― 純利益と ROE の推移",
                   x=0.0, xanchor="left", y=0.95, yanchor="top",
                   font=dict(size=18), pad=dict(b=12)),
        height=560, plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0.5, xanchor="center"),
        margin=dict(t=70, r=24, l=24, b=70), bargap=0.35,
    )
    fig.add_hline(y=0, line_color="#999999", line_width=1, secondary_y=False)
    fig.update_xaxes(title_text=None, showgrid=False)
    fig.update_yaxes(title_text="純利益（千億円）", secondary_y=False,
                     zeroline=False, showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(title_text="ROE（%）", secondary_y=True, showgrid=False)
    return fig


# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("## 7年業績チャート")
companies = scan_companies()

if not companies:
    st.warning("`data/yuho/{EDINETコード}/*.json` が見つかりません。"
               "有報 JSON を配置してください（再配布不可のため同梱していません）。")
    st.stop()

labels = {f"{name}（{ed}）": ed for ed, name in companies.items()}
default = next((k for k in labels if "E24050" in k), list(labels)[0])   # 既定 ＥＮＥＯＳ
sel = st.sidebar.selectbox("銘柄", list(labels), index=list(labels).index(default))
edinet = labels[sel]


# ── メイン ──────────────────────────────────────────────────
df = load_series(edinet)
if df.empty:
    st.warning("時系列データを読み込めませんでした。")
    st.stop()

st.plotly_chart(make_fig(df, companies[edinet]), use_container_width=True)

with st.expander("数値テーブル"):
    show = pd.DataFrame({
        "会計年度": df["fy"],
        "純利益（億円）": (df["net_income"].astype(float) / 1e8).round(0),
        "ROE（%）": (df["roe"].astype(float) * 100).round(1),
    })
    st.dataframe(show, use_container_width=True, hide_index=True)
