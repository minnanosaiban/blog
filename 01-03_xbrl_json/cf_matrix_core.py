"""CFマトリクス（営業CF × 投資CF）アプリのコア。

Streamlit 非依存（データ索引と Plotly 図のみ）。単体テスト・再利用しやすいよう
UI から分離している。

- build_index: data/yuho/{EDINET}/*.json を走査し 証券コード -> 系列 に索引化
- cf_matrix_fig: 1 社の「営業CF × 投資CF」7 年軌跡（バブル＝現金）を Plotly 図に
"""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go

# 連載のチャート配色（先頭 3 つは コスモ緑/ENEOS青/出光赤 と別系統の汎用色）
PALETTE = ["#3498db", "#5a9a72", "#c87878", "#9B59B6", "#F5A623",
           "#1ABC9C", "#E05C5C", "#4C8BF5", "#8C8C8C"]


def fix_name(s: str | None) -> str:
    """Shift-JIS バイトが Latin-1 として誤保存された社名を修復する。正常名はそのまま。"""
    if not s:
        return ""
    try:
        return s.encode("latin-1").decode("cp932")
    except Exception:
        return s


# 連載で使う短縮社名（同梱 13 社）。未登録は full から機械的に短縮する
SHORT_NAMES = {
    "1605": "INPEX", "1662": "石油資源開発", "2768": "双日",
    "5019": "出光興産", "5020": "ＥＮＥＯＳ", "5021": "コスモエネＨＤ",
    "8001": "伊藤忠", "8002": "丸紅", "8015": "豊田通商", "8020": "兼松",
    "8031": "三井物産", "8053": "住友商事", "8058": "三菱商事",
}


def short_name(sec: str, full: str | None) -> str:
    """証券コードから連載準拠の短縮名を返す。未登録は接尾辞を削って短縮。"""
    if sec in SHORT_NAMES:
        return SHORT_NAMES[sec]
    s = fix_name(full)
    return (s.replace("株式会社", "")
             .replace("ホールディングス", "ＨＤ").strip()) or s


def build_index(yuho_dir: Path) -> dict:
    """data/yuho/{EDINET}/*.json を走査し、証券コード -> {name, edinet, rows} を返す。

    rows は営業CF・投資CFが揃う年のみ、年度昇順。
    """
    idx: dict[str, dict] = {}
    for f in Path(yuho_dir).glob("*/*.json"):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        m = d.get("metadata", {}) or {}
        fin = d.get("financials", {}) or {}
        sec = str(m.get("sec_code") or "").strip()
        if not sec:
            continue
        e = idx.setdefault(sec, {
            "name": short_name(sec, m.get("company_name")),
            "edinet": m.get("edinet_code", ""),
            "rows": [],
        })
        e["rows"].append({
            "fy": (m.get("fiscal_year_end") or "")[:4],
            "op": fin.get("operating_cf"),
            "inv": fin.get("investing_cf"),
            "fin": fin.get("financing_cf"),
            "cash": fin.get("cash_end"),
        })
    for e in idx.values():
        e["rows"] = sorted(
            [r for r in e["rows"] if r["op"] is not None and r["inv"] is not None],
            key=lambda r: r["fy"],
        )
    return idx


def axis_ranges(entries: list[dict]) -> tuple[tuple[float, float], tuple[float, float]]:
    """複数社で共通の軸範囲（0 を必ず含む、単位＝億円）。比較モードで使う。"""
    xs, ys = [], []
    for e in entries:
        for r in e["rows"]:
            xs.append(r["op"] / 1e8)
            ys.append(r["inv"] / 1e8)
    if not xs:
        return (-1000.0, 1000.0), (-1000.0, 1000.0)
    xlo, xhi = min(xs + [0.0]), max(xs + [0.0])
    ylo, yhi = min(ys + [0.0]), max(ys + [0.0])
    px = 0.10 * ((xhi - xlo) or 1.0)
    py = 0.12 * ((yhi - ylo) or 1.0)
    return (xlo - px, xhi + px), (ylo - py, yhi + py)


def cf_matrix_fig(entry: dict, color: str = "#3498db",
                  xrange=None, yrange=None, height: int = 300) -> go.Figure:
    """1 社のCFマトリクス（営業CF × 投資CF の年次軌跡、バブル＝現金）を返す。"""
    rows = entry["rows"]
    x = [r["op"] / 1e8 for r in rows]
    y = [r["inv"] / 1e8 for r in rows]
    cash = [(r["cash"] or 0) / 1e8 for r in rows]
    fys = [r["fy"] for r in rows]
    fcf = [xi + yi for xi, yi in zip(x, y)]

    if xrange is None or yrange is None:
        xrange, yrange = axis_ranges([entry])

    fig = go.Figure()

    # FCF=0 の対角線（右上＝フリーCF プラス側）
    xr0, xr1 = xrange
    fig.add_trace(go.Scatter(
        x=[xr0, xr1], y=[-xr0, -xr1], mode="lines",
        line=dict(color="#9ccbe8", width=1, dash="dot"),
        hoverinfo="skip", showlegend=False,
    ))

    # 象限線
    fig.add_hline(y=0, line=dict(color="#9aa0a6", width=1))
    fig.add_vline(x=0, line=dict(color="#9aa0a6", width=1))

    # 軌跡 + 現金バブル。ラベルは端の年（最初/最後）のみ、途中はホバーで
    sizes = [max(9, min(40, c * 0.004)) for c in cash]
    disp = ["" for _ in fys]
    if fys:
        disp[0], disp[-1] = fys[0], fys[-1]
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers+text",
        line=dict(color=color, width=1.3),
        marker=dict(size=sizes, color=color, opacity=0.55,
                    line=dict(color="white", width=1.2)),
        text=disp, textposition="top center", textfont=dict(size=10),
        customdata=list(zip(cash, fcf, fys)),
        hovertemplate=("%{customdata[2]} 年<br>営業CF %{x:,.0f} 億<br>投資CF %{y:,.0f} 億"
                       "<br>FCF %{customdata[1]:,.0f} 億<br>現金 %{customdata[0]:,.0f} 億"
                       "<extra></extra>"),
        showlegend=False,
    ))

    fig.update_layout(
        height=height,
        margin=dict(t=10, b=34, l=10, r=10),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title="営業CF（億円）", range=list(xrange), zeroline=False,
                   gridcolor="rgba(0,0,0,0.05)"),
        yaxis=dict(title="投資CF（億円）", range=list(yrange), zeroline=False,
                   gridcolor="rgba(0,0,0,0.05)"),
    )
    return fig
