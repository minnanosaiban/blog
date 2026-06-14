"""
blog/18_enterprise_value.md（連載 2-8 企業価値分析）用の画像生成スクリプト。

生成画像:
  01_ev_composition.png  — 13社の EV 構成（時価総額 + ネットデット）
  02_ev_ocf.png          — EV / 営業CF 倍率（直近3期のばらつき）
  03_dcf_vs_ev.png       — 簡易DCF（各期FCFの永続価値）と市場EVの比較

データ:
  - 有報 JSON（data/yuho、2025年3月期末・INPEXのみ2025年12月期）
      ネットデット（有利子負債・リース・現金）、営業CF・投資CF 5期分
  - 決算短信 JSON（data/statements、2026年3月期）: 最新の株式数（自己株控除後）
  - 株価 parquet（data/prices/stocks/daily）: 最新終値

実行: python make_images.py
データパスは冒頭の定数（YUHO / STMTS / PRICES / SPLITS）を環境に合わせて変更してください。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import _blog_style as bs

# ── デザイン設定 ────────────────────────────────────────────────────────────
bs.apply_rcparams()
FIG_W = bs.FIG_W

C_OIL  = "#3498db"   # 元売（青）
C_SOGO = "#7f8c8d"   # 商社（灰）
C_RES  = "#b08968"   # 資源（茶）
C_DEBT = "#c87878"   # ネットデット（赤系）
C_CASH = "#5a9a72"   # ネットキャッシュ（緑系）
C_TEXT = "#202124"
C_TEXT_SUB = "#70757a"
C_GRID = "#eaeaea"

# ── データパス（環境に合わせて変更してください） ─────────────────────────
ROOT   = Path(r"C:/stock_analysis")
YUHO   = ROOT / "data" / "yuho"
STMTS  = ROOT / "data" / "statements"
PRICES = ROOT / "data" / "prices" / "stocks" / "daily"
SPLITS = ROOT / "data" / "master" / "stock_splits.csv"

OUT_DIR = Path(r"C:/minnanosaiban/hotline/docs/blog/posts/img/18_enterprise_value")
OUT_DIR.mkdir(parents=True, exist_ok=True)

_savefig_vpad = bs.savefig_uniform

# (edinet, code, 表示名, グループ)
COMPANIES = [
    ("E24050", "5020", "ＥＮＥＯＳ",   "元売"),
    ("E01084", "5019", "出光興産",     "元売"),
    ("E31632", "5021", "コスモエネＨＤ", "元売"),
    ("E02497", "8001", "伊藤忠商事",   "商社"),
    ("E02513", "8031", "三井物産",     "商社"),
    ("E02529", "8058", "三菱商事",     "商社"),
    ("E02528", "8053", "住友商事",     "商社"),
    ("E02498", "8002", "丸紅",         "商社"),
    ("E02505", "8015", "豊田通商",     "商社"),
    ("E02506", "8020", "兼松",         "商社"),
    ("E02958", "2768", "双日",         "商社"),
    ("E00043", "1605", "ＩＮＰＥＸ",   "資源"),
    ("E00041", "1662", "石油資源開発", "資源"),
]
GROUP_COLOR = {"元売": C_OIL, "商社": C_SOGO, "資源": C_RES}

DEBT_KEYS = [
    "interest_bearing_debt_current", "interest_bearing_debt_noncurrent",
    "current_portion_lt_debt", "current_portion_lt_loans",
    "bonds_payable", "commercial_papers", "current_portion_of_bonds",
]
LEASE_KEYS = ["lease_liabilities_current", "lease_liabilities_noncurrent"]

DCF_R = 0.07   # 簡易DCFの割引率（g=0 の永続価値: FCF / r）


# ══════════════════════════════════════════════════════════════════════════════
# データ読み込み
# ══════════════════════════════════════════════════════════════════════════════

def _load_splits() -> dict[str, float]:
    """sec_code → 分割比率（有報XBRLのBPSが分割前ベースの社のみ記載あり）。"""
    out: dict[str, float] = {}
    with open(SPLITS, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[row["sec_code"].strip()] = float(row["ratio"])
    return out


def _yuho_years(edinet: str) -> list[dict]:
    """有報の年度別 financials を期末日昇順で返す。"""
    out = []
    for f in sorted((YUHO / edinet).glob(f"{edinet}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append({"fy_end": d["metadata"]["fiscal_year_end"],
                    "std": d["metadata"]["accounting_standard"],
                    "fin": d.get("financials", {}) or {}})
    return out


def _shares_now(code: str, latest: dict, splits: dict[str, float]) -> tuple[float, str]:
    """現在の株式数（自己株控除後）を返す。短信があれば短信、なければ有報BPS逆算。"""
    stmt = STMTS / f"{code}_2026-03-31_FY.json"
    if stmt.exists():
        sh = json.loads(stmt.read_text(encoding="utf-8")).get("shares", {}) or {}
        issued, ts = sh.get("issued_at_period_end"), sh.get("treasury_at_period_end") or 0
        if issued:
            return issued - ts, "短信2026/3期末"
    fin, std = latest["fin"], latest["std"]
    eq = fin.get("net_assets") or 0
    if std == "JP":
        eq -= fin.get("noncontrolling_interests") or 0  # JPのnet_assetsはNCI込み
    n = eq / fin["bps"]
    # 有報XBRLのBPSは分割前ベースの社がある（stock_splits.csv 記載分）
    n *= splits.get(code, 1.0)
    return n, "有報BPS逆算"


def _price_latest(code: str) -> tuple[float, str]:
    sp = pd.read_parquet(PRICES / f"{code}.parquet", columns=["Close"])
    return float(sp["Close"].iloc[-1]), str(sp.index[-1])[:10]


def load_dataset() -> pd.DataFrame:
    splits = _load_splits()
    rows = []
    for edinet, code, name, group in COMPANIES:
        years = _yuho_years(edinet)
        latest = years[-1]
        fin = latest["fin"]
        gross = sum(fin.get(k) or 0 for k in DEBT_KEYS)
        lease = sum(fin.get(k) or 0 for k in LEASE_KEYS)
        cash = fin.get("cash_end") or 0
        net_debt = gross - cash          # 主軸はリース除き（リースは別掲）
        shares, sh_src = _shares_now(code, latest, splits)
        px, px_date = _price_latest(code)
        mktcap = px * shares
        ev = mktcap + net_debt

        # 直近5期の 営業CF・FCF（= 営業CF + 投資CF）
        ocf_hist, fcf_hist = {}, {}
        for y in years[-5:]:
            ocf, icf = y["fin"].get("operating_cf"), y["fin"].get("investing_cf")
            fy = y["fy_end"][:4]
            if ocf is not None:
                ocf_hist[fy] = ocf
                if icf is not None:
                    fcf_hist[fy] = ocf + icf

        rows.append({
            "code": code, "name": name, "group": group,
            "fy_end": latest["fy_end"], "gross_debt": gross, "lease": lease,
            "cash": cash, "net_debt": net_debt, "shares": shares,
            "shares_src": sh_src, "price": px, "price_date": px_date,
            "mktcap": mktcap, "ev": ev,
            "ocf_hist": ocf_hist, "fcf_hist": fcf_hist,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 図 1: EV 構成（時価総額 + ネットデット）
# ══════════════════════════════════════════════════════════════════════════════

def fig1_ev_composition(df: pd.DataFrame) -> None:
    d = df.sort_values("ev").reset_index(drop=True)
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(FIG_W, 7.6))

    cho = 1e12  # 兆円
    for i, r in d.iterrows():
        ax.barh(i, r["mktcap"] / cho, color=GROUP_COLOR[r["group"]], height=0.62)
        nd = r["net_debt"] / cho
        if nd >= 0:
            ax.barh(i, nd, left=r["mktcap"] / cho, color=C_DEBT, height=0.62)
        else:
            # ネットキャッシュは時価総額バーの右端に「控除分」として重ね、
            # EV の位置（バー内）に黒のマーカーを立てて加算と誤読されないようにする
            ax.barh(i, nd, left=r["mktcap"] / cho, color=C_CASH, height=0.62)
            ax.plot([r["ev"] / cho] * 2, [i - 0.4, i + 0.4],
                    color=C_TEXT, lw=2.2, zorder=5)
        ax.text(max(r["ev"], r["mktcap"]) / cho + 0.25, i,
                f"EV {r['ev']/cho:,.1f}兆円", va="center", fontsize=14, color=C_TEXT)

    ax.set_yticks(y)
    ax.set_yticklabels(d["name"])
    ax.set_xlabel("兆円")
    ax.set_title("EV（企業価値）の構成 ― 時価総額にネットデットを足す", color=C_TEXT)
    ax.grid(axis="x", color=C_GRID)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_xlim(-1.5, d["ev"].max() / cho * 1.18)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=C_OIL,  label="時価総額（元売）"),
        Patch(color=C_SOGO, label="時価総額（商社）"),
        Patch(color=C_RES,  label="時価総額（資源）"),
        Patch(color=C_DEBT, label="ネットデット（有利子負債−現金）"),
        Patch(color=C_CASH, label="ネットキャッシュ（緑の分だけ EV は時価総額より小さい。黒線＝EV）"),
    ], loc="lower right", frameon=False, fontsize=14)
    _savefig_vpad(fig, OUT_DIR / "01_ev_composition.png")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 図 2: EV / 営業CF 倍率（直近3期のばらつき）
# ══════════════════════════════════════════════════════════════════════════════

def fig2_ev_ocf(df: pd.DataFrame) -> None:
    rows = []
    for _, r in df.iterrows():
        fys = sorted(r["ocf_hist"])[-3:]
        ratios = {fy: r["ev"] / r["ocf_hist"][fy] for fy in fys if r["ocf_hist"][fy] != 0}
        rows.append({"name": r["name"], "group": r["group"], "ratios": ratios,
                     "latest": list(ratios.values())[-1] if ratios else np.nan})
    d = pd.DataFrame(rows).sort_values("latest", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(FIG_W, 7.6))
    XMAX = 40
    for i, r in d.iterrows():
        vals = list(r["ratios"].values())
        col = GROUP_COLOR[r["group"]]
        inside = [v for v in vals if 0 < v <= XMAX]
        if len(inside) >= 2:
            ax.plot([min(inside), max(inside)], [i, i], color=col, lw=2.5, alpha=0.45, zorder=2)
        for fy, v in r["ratios"].items():
            is_latest = (fy == max(r["ratios"]))
            if v < 0:   # 営業CFマイナスの期は左端の矢印で示す（脚注参照）
                ax.annotate("", xy=(0.08, i), xytext=(1.0, i),
                            arrowprops=dict(arrowstyle="->", color=col, lw=2))
                continue
            if v > XMAX:
                ax.annotate("", xy=(XMAX, i), xytext=(XMAX - 1.2, i),
                            arrowprops=dict(arrowstyle="->", color=col, lw=2))
                ax.text(XMAX - 1.4, i + 0.32, f"{v:,.0f}倍", fontsize=12, color=col, ha="right")
                continue
            ax.scatter(v, i, s=130 if is_latest else 60, color=col,
                       zorder=3, edgecolors="white", linewidths=1.2,
                       alpha=1.0 if is_latest else 0.55)
        if r["ratios"]:
            v = list(r["ratios"].values())[-1]
            if 0 < v <= XMAX:
                ax.text(v + 0.6, i, f"{v:.1f}倍", va="center", fontsize=14, color=C_TEXT)

    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["name"])
    ax.invert_yaxis()
    ax.set_xlim(0, XMAX)
    ax.set_xlabel("EV ÷ 営業CF（倍） ― 大きい点＝直近期、小さい点＝過去2期\n"
                  "左端の ← ＝その期は営業CFがマイナス（倍率を定義できない）　"
                  "右端の → ＝営業CFが小さすぎて軸の範囲外（数値は矢印の脇）")
    ax.set_title("会社の値段は「営業キャッシュフローの何年分」か", color=C_TEXT)
    ax.grid(axis="x", color=C_GRID)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    _savefig_vpad(fig, OUT_DIR / "02_ev_ocf.png")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 図 3: 簡易 DCF（各期 FCF の永続価値）と市場 EV
# ══════════════════════════════════════════════════════════════════════════════

def fig3_dcf_vs_ev(df: pd.DataFrame) -> None:
    rows = []
    for _, r in df.iterrows():
        vals = {fy: (fcf / DCF_R) / r["ev"] for fy, fcf in r["fcf_hist"].items()}
        if not vals:
            continue
        rows.append({"name": r["name"], "group": r["group"], "vals": vals,
                     "med": float(np.median(list(vals.values())))})
    d = pd.DataFrame(rows).sort_values("med", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(FIG_W, 7.6))
    XMIN, XMAX = -1.0, 3.2
    ax.axvline(1.0, color=C_TEXT, lw=1.5, ls="--", alpha=0.7, zorder=1)
    ax.text(1.02, len(d) - 0.62, "↑ 市場のEVと同じ", ha="left", fontsize=14, color=C_TEXT)
    ax.axvspan(XMIN, 0, color="#f5eaea", zorder=0)
    ax.text(XMIN + 0.04, -0.62, "FCFがマイナスの期", ha="left", fontsize=13, color="#a07070")

    for i, r in d.iterrows():
        col = GROUP_COLOR[r["group"]]
        vals = list(r["vals"].values())
        lo, hi = min(vals), max(vals)
        ax.plot([max(lo, XMIN), min(hi, XMAX)], [i, i], color=col, lw=3, alpha=0.4, zorder=2)
        for fy, v in r["vals"].items():
            is_latest = (fy == max(r["vals"]))
            if v < XMIN:
                ax.annotate("", xy=(XMIN, i), xytext=(XMIN + 0.12, i),
                            arrowprops=dict(arrowstyle="->", color=col, lw=2))
                continue
            if v > XMAX:
                ax.annotate("", xy=(XMAX, i), xytext=(XMAX - 0.12, i),
                            arrowprops=dict(arrowstyle="->", color=col, lw=2))
                ax.text(XMAX - 0.14, i + 0.32, f"{v:.1f}", fontsize=12, color=col, ha="right")
                continue
            ax.scatter(v, i, s=130 if is_latest else 60, color=col, zorder=3,
                       edgecolors="white", linewidths=1.2,
                       alpha=1.0 if is_latest else 0.55)

    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["name"])
    ax.invert_yaxis()
    ax.set_xlim(XMIN, XMAX)
    ax.set_xlabel(f"その期のFCFが永遠に続くと仮定した価値 ÷ 市場のEV（割引率{DCF_R:.0%}・成長0%）")
    ax.set_title("簡易DCF ― 「いまのFCFが続くなら」を市場の値付けと突き合わせる", color=C_TEXT)
    ax.grid(axis="x", color=C_GRID)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    _savefig_vpad(fig, OUT_DIR / "03_dcf_vs_ev.png")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    df = load_dataset()
    cho = 1e12
    print(f"{'code':<5} {'name':<8} {'株価日付':<11} {'時価総額':>7} {'ネットデット':>7} "
          f"{'EV':>7} {'EV/OCF':>7} {'株数源'}")
    for _, r in df.iterrows():
        fys = sorted(r["ocf_hist"])
        ratio = r["ev"] / r["ocf_hist"][fys[-1]] if fys else float("nan")
        print(f"{r['code']:<5} {r['name']:<8} {r['price_date']:<11} "
              f"{r['mktcap']/cho:>6.2f}兆 {r['net_debt']/cho:>6.2f}兆 "
              f"{r['ev']/cho:>6.2f}兆 {ratio:>6.1f}倍  {r['shares_src']}")
    fig1_ev_composition(df)
    fig2_ev_ocf(df)
    fig3_dcf_vs_ev(df)
    print(f"\nsaved -> {OUT_DIR}")


if __name__ == "__main__":
    main()
