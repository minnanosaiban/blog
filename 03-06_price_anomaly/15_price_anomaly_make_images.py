# -*- coding: utf-8 -*-
"""
連載 3-6 突発材料の異常検知 ― 画像生成（hotline の img フォルダへ出力）

「市場・同業は動いていないのに、その銘柄だけ突発的に上げ下げした日」を検出する。
不正に限らず、買収・TOB・業績修正・事故など個別材料が出た銘柄のトリアージ。
3-2 の個別ショック検出器の、決算に依らない毎日・全銘柄版。予測ではなく検出。

入力:
  data/blog15/features.parquet, data/prices/stocks/daily/*.parquet, data/master/sectors/*.csv
出力:
  docs/blog/posts/img/15_price_anomaly/ :
    00_thumbnail / 01_mechanism / 02_event_casestudy /
    03_sudden_events / 04_eneos_decoupling / 05_daily_monitor
  data/blog19/anomaly_events.csv, eneos_decoupling.csv
"""
from __future__ import annotations

import sys
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA

import _blog_style as bs

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
B15 = ROOT / "data" / "blog15"
DAILY = ROOT / "data" / "prices" / "stocks" / "daily"
SECT = ROOT / "data" / "master" / "sectors"
DATA_OUT = ROOT / "data" / "blog19"
IMG = Path("C:/minnanosaiban/hotline/docs/blog/posts/img/15_price_anomaly")
DATA_OUT.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

WINDOW = 500
MIN_COVER = 0.95
N_CLUSTERS = 12
N_PC = 10
ENEOS, IDEMITSU, COSMO = "5020", "5019", "5021"
FEATURE_COLS = [
    "net_sales_yoy", "operating_yoy", "pretax_yoy", "net_income_yoy",
    "comprehensive_yoy", "div_growth_pct", "op_margin", "net_margin",
    "segment_count", "max_seg_share",
]
EXTRA = [IDEMITSU, COSMO, "8002", "2768", "7203", "6758", "8306", "9501", "9984"]


def short_name(raw, code: str, width: int = 8) -> str:
    """y軸ラベル用の短縮社名。法人格を落とし、固定幅で切らずに省略記号を付ける。"""
    s = "" if raw is None else str(raw)
    if not s or s == "nan":
        s = code
    for tok in ("株式会社", "（株）", "(株)"):
        s = s.replace(tok, "")
    s = (s.replace("ホールディングス", "HD").replace("ホールディング", "HD")
          .replace("フィナンシャルグループ", "FG").replace("グループ", "G")
          .strip())
    return s if len(s) <= width else s[: width - 1] + "…"


def load_universe():
    feat = pd.read_parquet(B15 / "features.parquet")
    feat["code"] = feat["code"].astype(str)
    uni = feat.dropna(subset=FEATURE_COLS, thresh=7)
    name = dict(zip(uni["code"], uni["company"].astype(str)))
    codes = [c for c in uni["code"] if (DAILY / f"{c}.parquet").exists()]
    for c in EXTRA:
        if c not in codes and (DAILY / f"{c}.parquet").exists():
            codes.append(c)
    return codes, name


def load_sectors():
    code2sec = {}
    for csv in SECT.glob("*.csv"):
        try:
            df = pd.read_csv(csv, encoding="utf-8", dtype=str)
        except Exception:
            continue
        if df.shape[1] < 4:
            continue
        cc, sc = df.columns[0], df.columns[3]
        for _, r in df.iterrows():
            c = str(r[cc]).strip()
            if c and c not in code2sec:
                code2sec[c] = str(r[sc]).strip()
    return code2sec


def build_returns(codes):
    closes = {}
    for c in codes:
        try:
            closes[c] = pd.read_parquet(DAILY / f"{c}.parquet")["Close"].astype(float)
        except Exception:
            continue
    px = pd.DataFrame(closes).sort_index().tail(WINDOW)
    cover = px.notna().mean()
    px = px.loc[:, cover[cover >= MIN_COVER].index]
    return np.log(px).diff().iloc[1:].ffill().fillna(0.0)


def main():
    bs.apply_rcparams()
    FIG_W = bs.FIG_W
    codes, name = load_universe()
    code2sec = load_sectors()
    rets = build_returns(codes)
    cols = list(rets.columns)
    print(f"銘柄 {len(cols)} / 営業日 {len(rets)}  期間 {rets.index.min().date()}..{rets.index.max().date()}")

    # クラスタ（ケーススタディの「いつもの仲間」に使う）
    corr = rets.corr()
    D = np.sqrt(np.clip(2.0 * (1.0 - corr.values), 0, None)); np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="ward")
    clab = dict(zip(cols, fcluster(Z, t=N_CLUSTERS, criterion="maxclust")))

    # PCA 残差（異常度）
    Zret = (rets - rets.mean()) / rets.std(ddof=0).replace(0, 1)
    pca = PCA(n_components=N_PC, random_state=42).fit(Zret.values)
    recon = pca.inverse_transform(pca.transform(Zret.values))
    resid = pd.DataFrame(Zret.values - recon, index=rets.index, columns=cols)
    recon_df = Zret - resid
    evar = pca.explained_variance_ratio_
    print(f"PCA 上位{N_PC}本で分散 {evar.sum():.0%}（PC1={evar[0]:.0%}＝市場全体）")

    # 突発材料イベント（その日の実際/市場リターン付き）
    flat = resid.abs().stack().reset_index()
    flat.columns = ["date", "code", "score"]
    flat = flat.sort_values("score", ascending=False)
    ev = flat.head(50).copy()
    ev["name"] = ev["code"].map(name); ev["sector"] = ev["code"].map(code2sec)
    day_mkt = rets.mean(axis=1)
    ev["ret_pct"] = [float(np.expm1(rets.at[d, c]) * 100) for d, c in zip(ev.date, ev.code)]
    ev["mkt_pct"] = [float(np.expm1(day_mkt.at[d]) * 100) for d in ev.date]
    ev["excess_pct"] = ev["ret_pct"] - ev["mkt_pct"]
    ev["dir"] = np.where(ev["excess_pct"] >= 0, "急騰", "急落")
    ev.to_csv(DATA_OUT / "anomaly_events.csv", index=False, encoding="utf-8-sig")
    print("\n=== 突発材料 Top8 ===")
    for _, r in ev.head(8).iterrows():
        print(f"  {r.date.date()} {r.code} {str(r['name'])[:12]:<12} {r.ret_pct:+6.1f}%(市場{r.mkt_pct:+4.1f}%→個別{r.excess_pct:+6.1f}%) {r.dir} {r.score:4.1f}σ")

    # ENEOS デカップリング
    peers = [c for c in (IDEMITSU, COSMO) if c in cols]
    panel = None
    if ENEOS in cols and peers:
        peer = rets[peers].mean(axis=1); re = rets[ENEOS]; w = 60
        beta = re.rolling(w).cov(peer) / peer.rolling(w).var()
        panel = pd.DataFrame({"rollcorr60": re.rolling(w).corr(peer),
                              "resid_cum": (re - beta * peer).fillna(0).cumsum()})
        panel.to_csv(DATA_OUT / "eneos_decoupling.csv", encoding="utf-8-sig")
        print(f"ENEOS×石油ピア 相関平均 {panel['rollcorr60'].mean():.2f} / 最小 {panel['rollcorr60'].min():.2f}（{panel['rollcorr60'].idxmin().date()}）")

    # ===== 01 仕組み =====
    cc, cd, cs = "3382", pd.Timestamp("2024-08-19"), "セブン＆アイ"
    if cc in cols and cd in rets.index:
        pos = rets.index.get_loc(cd)
        win = rets.index[max(0, pos - 25): min(len(rets), pos + 16)]
        a, rc, rs = Zret.loc[win, cc], recon_df.loc[win, cc], resid.loc[win, cc]
        fig, axes = plt.subplots(2, 1, figsize=(FIG_W, FIG_W * 0.62), sharex=True, layout="constrained")
        ax0 = axes[0]
        ax0.bar(win, a.values, width=0.8, color="#b0c4de", label="実際の値動き（標準化 σ）")
        ax0.plot(win, rc.values, color="#1f4e79", lw=1.8, marker="o", ms=3, label="共通成分＝市場・業種で説明できる分（PCA再構成）")
        ax0.axvline(cd, color="#2c3e50", ls="--", lw=1.2); ax0.axhline(0, color="gray", lw=0.7)
        ax0.legend(fontsize=9, loc="upper left"); ax0.set_ylabel("σ")
        ax0.set_title(f"{cc} {cs}：実際の動きのうち『みんなと同じ分』はごくわずか（{cd.date()}）", fontsize=13)
        ax1 = axes[1]
        ax1.bar(win, rs.values, width=0.8, color=["#c0392b" if abs(v) >= 4 else "#9aa0a6" for v in rs.values])
        for s in (2, 5):
            ax1.axhline(s, color="gray", ls=":", lw=0.8); ax1.axhline(-s, color="gray", ls=":", lw=0.8)
        ax1.axvline(cd, color="#2c3e50", ls="--", lw=1.2)
        ax1.annotate(f"{abs(rs.loc[cd]):.0f}σ", (cd, rs.loc[cd]), fontsize=11, color="#c0392b", fontweight="bold", xytext=(5, -2), textcoords="offset points")
        ax0.set_ylim(top=ax0.get_ylim()[1] * 1.12)  # 異常日のバーが上枠に当たらないよう頭上を空ける
        ax1.set_ylabel("残差＝個別分 σ")
        ax1.set_title("残差＝実際 − 共通成分。これが大きい日＝個別材料が出た日（＝異常度）", fontsize=13)
        # 窓が約2か月なので月表示では同じラベルが並ぶ。日単位で表示する
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6)); ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        bs.savefig_uniform(fig, IMG / "01_mechanism.png")

    # ===== 02 ケーススタディ =====
    cases = [("3382", "2024-08-19", "セブン＆アイ"), ("6201", "2025-04-28", "豊田自動織機"),
             ("6135", "2025-05-09", "牧野フライス"), ("6807", "2025-10-31", "日本航空電子")]
    sector_members = {}
    for c in cols:
        sector_members.setdefault(code2sec.get(c), []).append(c)

    def peer_codes(c):
        mates = [x for x in cols if clab.get(x) == clab.get(c) and x != c]
        if len(mates) >= 3:
            return mates, "クラスタ平均（いつもの仲間）"
        sm = [x for x in sector_members.get(code2sec.get(c), []) if x != c]
        if len(sm) >= 3:
            return sm, "同業平均"
        return [x for x in cols if x != c], "市場平均"

    def rebased(s):
        cum = s.cumsum()
        return 100.0 * np.exp(cum - cum.iloc[0])

    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, FIG_W * 0.68), layout="constrained")
    for ax, (c, dstr, short) in zip(axes.ravel(), cases):
        d = pd.Timestamp(dstr)
        if c not in cols or d not in rets.index:
            ax.axis("off"); continue
        pos = rets.index.get_loc(d)
        win = rets.iloc[max(0, pos - 25): min(len(rets), pos + 16)]
        prs, plabel = peer_codes(c)
        ax.plot(win.index, rebased(win[prs].mean(axis=1)), color="#9aa0a6", lw=1.8, label=plabel)
        ax.plot(win.index, rebased(win[c]), color="#c0392b", lw=2.4, label=f"{c} {short}")
        ax.axvline(d, color="#2c3e50", ls="--", lw=1.2)
        chg = float(np.expm1(rets.at[d, c]) * 100)
        ax.set_title(f"{c} {short}  {dstr}  {chg:+.0f}%（{'急騰' if chg >= 0 else '急落'}）", fontsize=12)
        ax.legend(fontsize=8.5, loc="best"); ax.set_ylabel("株価（窓開始=100）", fontsize=9)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.tick_params(labelsize=8)
    fig.suptitle("突発材料のケーススタディ ― いつもの仲間は平らなのに、その銘柄だけ跳ねた／落ちた", fontsize=14)
    bs.savefig_uniform(fig, IMG / "02_event_casestudy.png")

    # ===== 03 突発材料 Top15 =====
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.62))
    t = ev.head(15).iloc[::-1]
    ax.barh(range(len(t)), t["excess_pct"], color=["#2e8b57" if v >= 0 else "#c0392b" for v in t["excess_pct"]])
    ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{d.date()}  {c} {short_name(n, c)}" for d, c, n in zip(t.date, t.code, t.name)], fontsize=13)
    ax.axvline(0, color="gray", lw=0.8); ax.set_xlabel("その日の個別超過リターン（銘柄 − 市場平均, %）")
    ax.set_title("突発材料 Top15 ― 市場が動いていないのに、その銘柄だけ急騰／急落した日", fontsize=14)
    for i, v in enumerate(t["excess_pct"]):
        ax.text(v + (0.4 if v >= 0 else -0.4), i, f"{v:+.0f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    bs.savefig_uniform(fig, IMG / "03_sudden_events.png")

    # ===== 04 ENEOS デカップリング =====
    if panel is not None:
        fig, axes = plt.subplots(2, 1, figsize=(FIG_W, FIG_W * 0.72), sharex=True)
        ax0 = axes[0]
        ax0.plot(panel.index, panel["rollcorr60"], color="#1f4e79", lw=1.6)
        ax0.axhline(panel["rollcorr60"].mean(), color="gray", ls="--", lw=1)
        ax0.set_ylabel("ENEOS×石油ピア\nローリング相関(60d)")
        ax0.set_title("ENEOS は石油ピアとどれだけ連動しているか ― 連動が切れた局面＝個別材料", fontsize=14)
        evd = pd.Timestamp("2025-03-28")
        for ax in axes:
            if panel.index.min() <= evd <= panel.index.max():
                ax.axvline(evd, color="#c0392b", ls=":", lw=1.4)
        # 縦書きで線上に置くと点線・折れ線と交錯するため、横書きで線の右脇上部に置く
        ax0.annotate("2025-03-28\n業績予想修正", (evd, ax0.get_ylim()[1]), fontsize=12,
                     color="#c0392b", ha="left", va="top",
                     xytext=(8, -4), textcoords="offset points")
        ax1 = axes[1]
        ax1.plot(panel.index, panel["resid_cum"], color="#c0504d", lw=1.6); ax1.axhline(0, color="gray", lw=0.8)
        ax1.set_ylabel("ピアで説明できない\n累積リターン（残差）")
        bs.savefig_uniform(fig, IMG / "04_eneos_decoupling.png")

    # ===== 05 運用ビュー =====
    breach3 = (resid.abs() >= 3).sum(axis=1); breach5 = (resid.abs() >= 5).sum(axis=1)
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.5), layout="constrained")
    ax.fill_between(resid.index, breach3.values, step="mid", color="#cbd5dc", label="|残差|≥3σ（要注目）")
    ax.bar(resid.index, breach5.values, width=1.0, color="#c0392b", label="|残差|≥5σ（強い個別ショック）")
    ax.set_ylabel(f"該当銘柄数 / 日（全{len(cols)}銘柄中）")
    ax.set_title("毎日の見張り ― その日『いつもと違う動き』をした銘柄数", fontsize=14)
    ax.legend(fontsize=9, loc="upper left")
    td = breach5.idxmax()
    # 最大日は系列の右端付近に出るため、右に出すと枠線に接触する。左側に置く
    ax.annotate(f"{td.date()} {int(breach5.max())}銘柄", (td, breach5.max()), fontsize=11,
                color="#c0392b", ha="right", xytext=(-6, 4), textcoords="offset points")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    bs.savefig_uniform(fig, IMG / "05_daily_monitor.png")

    # ===== 00 サムネイル =====
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_W * 0.5))
    ax.fill_between(resid.index, breach3.values, step="mid", color="#dde3e8")
    ax.bar(resid.index, breach5.values, width=1.0, color="#c0392b")
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.02, 0.95, "突発材料を検出する", transform=ax.transAxes, fontsize=30, fontweight="bold", va="top")
    ax.text(0.02, 0.81, "市場が動いていないのに、その銘柄だけ動いた日", transform=ax.transAxes, fontsize=15, va="top", color="#444")
    bs.savefig_uniform(fig, IMG / "00_thumbnail.png")

    print(f"\n画像: {IMG}")


if __name__ == "__main__":
    main()
