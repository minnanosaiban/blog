"""連載 番外編: CFマトリクス ― 営業CF × 投資CF を複数社“並べて”見る無料アプリ。

有報 XBRL（EDINET 公開データ）の data/yuho/ を読み、各社のキャッシュフローの軌跡を
ブラウザで並べて比較する。データは無料・公開で、fetch_yuho.py で誰でも追加取得できる。

起動: streamlit run app_cf_matrix.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from cf_matrix_core import build_index, cf_matrix_fig, axis_ranges, PALETTE

APP_DIR = Path(__file__).parent
YUHO_DIR = APP_DIR / "data" / "yuho"

st.set_page_config(page_title="CFマトリクス", page_icon="🗺️", layout="wide")

# 既定は 1100px に絞り、サイドバーの「Wide 表示」で全幅に（1-2 アプリと同じ作り）
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


@st.cache_data(show_spinner="📥 有報 JSON を読み込み中…")
def _index() -> dict:
    return build_index(YUHO_DIR)


idx = _index()

# ── サイドバー ──────────────────────────────────────────────
st.sidebar.markdown("# CFマトリクス")
st.sidebar.caption("営業CF × 投資CF で会社の局面を読む\n（無料・EDINET 公開データ）")

raw = st.sidebar.text_area(
    "証券コード", value="5020\n5021\n5019", height=160,
    help="カンマ・改行・スペース区切り。3 列グリッドで並べて比較します",
)
codes = [c.strip() for c in re.split(r"[,\s\n]+", raw) if c.strip()]
share = st.sidebar.checkbox("軸を揃えて比較", value=True,
                            help="3 社の X・Y 軸を共通化して位置を直接比較する")
st.sidebar.checkbox("Wide 表示", key="_wide_layout",
                    help="本文エリアを全幅に広げる")

if idx:
    st.sidebar.caption(f"同梱データ: {len(idx)} 社")

# ── メイン ──────────────────────────────────────────────────
st.markdown("**⬛ CFマトリクス ― 営業CF × 投資CF の軌跡（バブル＝現金）**")
st.caption("右下＝稼いで投資する健全な局面／左側＝営業CFがマイナス／点線より上＝フリーCFがプラス")

entries = [(c, idx[c]) for c in codes if c in idx]
missing = [c for c in codes if c not in idx]
if missing:
    st.warning(f"データが無い証券コード: {', '.join(missing)}　"
               "（data/yuho/ に有報 JSON が必要。fetch_yuho.py で取得できます）")
if not entries:
    st.info("👈 証券コードを入力してください")
    st.stop()

xr, yr = (axis_ranges([e for _, e in entries]) if share else (None, None))

# ── 3 列カードグリッド（2-2 アプリと同じ並べ方）────────────────
st.markdown(
    """<style>[data-testid="stHorizontalBlock"]{gap:.4rem!important}
    [data-testid="column"]{padding:0 .2rem!important}</style>""",
    unsafe_allow_html=True,
)

COLS = 3
for i in range(0, len(entries), COLS):
    chunk = entries[i:i + COLS]
    cols = st.columns(COLS, gap="small")
    for j, col in enumerate(cols):
        if j >= len(chunk):
            continue
        code, e = chunk[j]
        color = PALETTE[(i + j) % len(PALETTE)]
        with col:
            st.markdown(
                f"<div style='text-align:center;font-weight:700;line-height:1.2'>"
                f"{e['name']}"
                f"<span style='color:#70757a;font-size:.85em'>（{code}）</span></div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                cf_matrix_fig(e, color=color, xrange=xr, yrange=yr),
                use_container_width=True, config={"displayModeBar": False},
            )

# ── CF 明細テーブル（アコーディオンで格納）──────────────────
recs = []
for code, e in entries:
    for r in e["rows"]:
        recs.append({
            "コード": code, "会社": e["name"], "年度": r["fy"],
            "営業CF": round(r["op"] / 1e8),
            "投資CF": round(r["inv"] / 1e8),
            "財務CF": round((r["fin"] or 0) / 1e8),
            "FCF": round((r["op"] + r["inv"]) / 1e8),
            "現金": round((r["cash"] or 0) / 1e8),
        })
with st.expander("CF 明細（億円）を見る", expanded=False):
    st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
