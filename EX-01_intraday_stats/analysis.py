"""
番外編A（数値分析）: スキャルピング・シグナルの統計検証ハーネス。

5 分足（data/prices/stocks/5min/*.parquet, 2025-11-21〜2026-05-29, 65本/日）と
TDnet 開示ログ（data/news/tdnet/*.csv）だけで検証できる 5 実験を、
共通の IN/OUT 分割（IN: 〜2026-03-31 / OUT: 2026-04-01〜）とコスト控除で評価する。

  exp1  イントラデイ・シーズナリティ（時間帯ごとの平均リターン・ボラ）
  exp2  寄りギャップ → 寄り後 30 分の続伸/反転
  exp3  モメンタム vs 平均回帰（直近バー符号 → 次バー符号）
  exp4  セクター内リードラグ（元売・商社の 5 分足クロス相関）
  exp5  場中開示イベント・ドリフト（TDnet タイムスタンプ → 直後 30 分）

出力: data/blog20/ に中間 parquet と results_summary.md
実行: python scripts/blog20_scalping_stats.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\stock_analysis")
PRICE_DIR = ROOT / "data" / "prices" / "stocks" / "5min"
TDNET_DIR = ROOT / "data" / "news" / "tdnet"
OUT_DIR = ROOT / "data" / "blog20"
OUT_DIR.mkdir(parents=True, exist_ok=True)

IN_END = pd.Timestamp("2026-03-31")          # IN: これ以前 / OUT: 翌日以降
COSTS_BP = [0, 5, 10]                         # 往復コスト（bps）シナリオ
UNIVERSE_N = 300                              # 流動性上位ユニバース
MIN_DAYS = 100                                # 最低営業日数

# リードラグ対象（元売 3 社 + 総合商社）
LEADLAG_CODES = {
    "5020": "ＥＮＥＯＳ", "5019": "出光興産", "5021": "コスモエネＨＤ",
    "8001": "伊藤忠", "8002": "丸紅", "8031": "三井物産",
    "8053": "住友商事", "8058": "三菱商事", "2768": "双日", "8015": "豊田通商",
}


# ── キャッシュ構築: 全銘柄の Close / Volume ワイド表 ─────────────────────────
def build_cache() -> tuple[pd.DataFrame, pd.DataFrame]:
    f_close = OUT_DIR / "close_wide.parquet"
    f_vol = OUT_DIR / "volume_wide.parquet"
    if f_close.exists() and f_vol.exists():
        return pd.read_parquet(f_close), pd.read_parquet(f_vol)

    closes, vols = {}, {}
    files = sorted(PRICE_DIR.glob("*.parquet"))
    print(f"[cache] {len(files)} 銘柄を読み込み中...")
    for i, f in enumerate(files):
        code = f.stem
        try:
            df = pd.read_parquet(f, columns=["Close", "Volume"])
        except Exception:
            continue
        idx = df.index.tz_localize(None) if df.index.tz is not None else df.index
        df.index = idx
        df = df[~df.index.duplicated(keep="last")]
        closes[code] = df["Close"]
        vols[code] = df["Volume"]
        if (i + 1) % 300 == 0:
            print(f"  ... {i + 1}/{len(files)}")
    close = pd.DataFrame(closes).sort_index()
    vol = pd.DataFrame(vols).sort_index()
    close.to_parquet(f_close)
    vol.to_parquet(f_vol)
    print(f"[cache] close {close.shape} / volume {vol.shape} を保存")
    return close, vol


def pick_universe(close: pd.DataFrame, vol: pd.DataFrame) -> list[str]:
    """流動性（中央値の日次売買代金）上位 UNIVERSE_N 銘柄。"""
    turnover = (close * vol).groupby(close.index.date).sum()
    days_ok = (close.notna().groupby(close.index.date).any()).sum() >= MIN_DAYS
    med = turnover[days_ok.index[days_ok]].median()
    uni = med.nlargest(UNIVERSE_N).index.tolist()
    return uni


def bar_returns(close: pd.DataFrame) -> pd.DataFrame:
    """日をまたがない 5 分バーリターン。"""
    ret = close.pct_change(fill_method=None)
    # 日付が変わる最初のバーはオーバーナイトを含むので除外
    dates = pd.Series(close.index.date, index=close.index)
    first_of_day = dates.ne(dates.shift())
    ret[first_of_day.values] = np.nan
    return ret


def split_in_out(index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    is_in = index.normalize() <= IN_END
    return is_in, ~is_in


def net_of_cost(gross_per_trade: float, cost_bp: float) -> float:
    return gross_per_trade - cost_bp / 1e4


# ── exp1: イントラデイ・シーズナリティ ───────────────────────────────────────
def exp1_seasonality(ret: pd.DataFrame, uni: list[str]) -> dict:
    r = ret[uni]
    tod = r.index.strftime("%H:%M")
    is_in, is_out = split_in_out(r.index)

    mean_in = r[is_in].groupby(tod[is_in]).mean().mean(axis=1) * 1e4   # bps
    mean_out = r[is_out].groupby(tod[is_out]).mean().mean(axis=1) * 1e4
    vol_by_tod = r.std().mean() * 1e4  # 参考: 全体バーボラ
    tbl = pd.DataFrame({"in_bps": mean_in, "out_bps": mean_out})
    tbl.to_parquet(OUT_DIR / "exp1_seasonality.parquet")

    # IN で符号の大きい上位/下位 5 バケツが OUT でも同符号か
    top = mean_in.nlargest(5)
    bot = mean_in.nsmallest(5)
    top_hold = int((mean_out[top.index] > 0).sum())
    bot_hold = int((mean_out[bot.index] < 0).sum())
    corr = float(tbl.dropna().corr().iloc[0, 1])
    return {
        "bar_vol_bps": round(float(vol_by_tod), 2),
        "in_top5": {k: round(v, 2) for k, v in top.items()},
        "in_bot5": {k: round(v, 2) for k, v in bot.items()},
        "out_same_sign_top5": top_hold, "out_same_sign_bot5": bot_hold,
        "in_out_corr": round(corr, 3),
    }


# ── exp2: 寄りギャップ → 寄り後 30 分 ────────────────────────────────────────
def exp2_gap(close: pd.DataFrame, uni: list[str]) -> dict:
    c = close[uni]
    dates = pd.Series(c.index.date, index=c.index)
    grp = c.groupby(dates.values)
    day_open = grp.first()       # 始値近似 = 最初のバー Close
    day_close = grp.last()
    # 寄り後 30 分: 各日 7 本目（位置 6）の Close / 最初のバー Close - 1
    pos = grp.cumcount()
    c7 = c[(pos == 6).values].copy()
    c7.index = dates[(pos == 6).values].values
    day7 = c7.reindex(day_open.index)
    r30 = day7 / day_open - 1
    gap = day_open / day_close.shift(1) - 1
    days = pd.to_datetime(pd.Index(day_open.index))
    is_in = np.asarray(days <= IN_END)

    g = pd.DataFrame({"gap": gap.values.ravel(), "r30": r30.values.ravel(),
                      "is_in": np.repeat(is_in, len(uni))}).dropna()
    g = g[np.abs(g["gap"]) < 0.15]
    # ギャップ十分位 → 30 分リターン
    g["dec"] = pd.qcut(g["gap"], 10, labels=False, duplicates="drop")
    dec_in = g[g.is_in].groupby("dec")[["gap", "r30"]].mean() * 1e4
    dec_out = g[~g.is_in].groupby("dec")[["gap", "r30"]].mean() * 1e4
    pd.concat({"in": dec_in, "out": dec_out}, axis=1).to_parquet(OUT_DIR / "exp2_gap_deciles.parquet")

    corr_in = float(g[g.is_in][["gap", "r30"]].corr().iloc[0, 1])
    corr_out = float(g[~g.is_in][["gap", "r30"]].corr().iloc[0, 1])
    # ルール: IN の符号（corr<0 なら逆張り）で OUT の大ギャップ日 (|gap|>1%) を取引
    fade = corr_in < 0
    big = g[(~g.is_in) & (g["gap"].abs() > 0.01)]
    sig = -np.sign(big["gap"]) if fade else np.sign(big["gap"])
    per_trade = float((sig * big["r30"]).mean())
    res = {"corr_in": round(corr_in, 3), "corr_out": round(corr_out, 3),
           "rule": "fade(逆張り)" if fade else "follow(順張り)",
           "out_trades": int(len(big)),
           "out_per_trade_bps": round(per_trade * 1e4, 2),
           "net_bps": {f"{c}bp": round(net_of_cost(per_trade, c) * 1e4, 2) for c in COSTS_BP}}
    return res


# ── exp3: モメンタム vs 平均回帰 ─────────────────────────────────────────────
def exp3_momentum(ret: pd.DataFrame, uni: list[str]) -> dict:
    r = ret[uni]
    is_in, is_out = split_in_out(r.index)
    # lag-1 自己相関の分布（IN）
    ac1 = r[is_in].apply(lambda s: s.autocorr(1))
    res = {"ac1_median_in": round(float(ac1.median()), 4),
           "ac1_negative_share_in": round(float((ac1 < 0).mean()), 3)}

    out = {}
    for k in (1, 3, 6):
        sig = np.sign(r.rolling(k).sum()).shift(0)
        nxt = r.shift(-1)
        mask = is_out[:, None] & sig.notna().values & nxt.notna().values & (sig != 0).values
        s = sig.values[mask]
        x = nxt.values[mask]
        mom = float((s * x).mean())            # 順張り 1 バー保有
        hit = float(((s * x) > 0).mean())
        out[f"k={k}"] = {
            "direction": "momentum" if mom > 0 else "mean-reversion",
            "edge_bps_momentum": round(mom * 1e4, 3),
            "hit_rate_momentum": round(hit, 4),
            "trades": int(mask.sum()),
            "net_bps_bestside": {f"{c}bp": round((abs(mom) - c / 1e4) * 1e4, 3) for c in COSTS_BP},
        }
    res["out_sample"] = out
    return res


# ── exp4: セクター内リードラグ ───────────────────────────────────────────────
def exp4_leadlag(ret: pd.DataFrame) -> dict:
    codes = [c for c in LEADLAG_CODES if c in ret.columns]
    r = ret[codes].dropna(how="all")
    is_in, is_out = split_in_out(r.index)
    rin, rout = r[is_in], r[is_out]

    rows = []
    for a in codes:
        for b in codes:
            if a == b:
                continue
            c_in = rin[a].corr(rin[b].shift(-1))
            rows.append({"lead": a, "lag": b, "corr_in": c_in})
    ll = pd.DataFrame(rows).dropna().sort_values("corr_in", ascending=False)
    ll.to_parquet(OUT_DIR / "exp4_leadlag_pairs.parquet")

    # IN 上位 3 ペアを OUT で検証（リード銘柄の符号 → ラグ銘柄の次バー）
    top3 = ll.head(3)
    checks = []
    for _, p in top3.iterrows():
        sig = np.sign(rout[p["lead"]])
        nxt = rout[p["lag"]].shift(-1)
        m = sig.notna() & nxt.notna() & (sig != 0)
        per_trade = float((sig[m] * nxt[m]).mean())
        checks.append({
            "pair": f"{LEADLAG_CODES[p['lead']]}→{LEADLAG_CODES[p['lag']]}",
            "corr_in": round(float(p["corr_in"]), 4),
            "out_per_trade_bps": round(per_trade * 1e4, 3),
            "out_hit": round(float(((sig[m] * nxt[m]) > 0).mean()), 4),
            "trades": int(m.sum()),
            "net_bps": {f"{c}bp": round(net_of_cost(per_trade, c) * 1e4, 3) for c in COSTS_BP},
        })
    return {"pairs_tested": len(ll), "corr_in_max": round(float(ll.corr_in.max()), 4),
            "corr_in_median": round(float(ll.corr_in.median()), 4),
            "top3_out_check": checks}


# ── exp5: 場中開示イベント・ドリフト ─────────────────────────────────────────
def exp5_event_drift(close: pd.DataFrame, ret: pd.DataFrame, uni: list[str]) -> dict:
    rows = []
    for f in sorted(TDNET_DIR.glob("*.csv")):
        if not ("2025-11-21" <= f.stem <= "2026-05-29"):
            continue
        try:
            df = pd.read_csv(f, dtype=str)
        except Exception:
            continue
        if df.empty:
            continue
        df["date"] = f.stem
        rows.append(df)
    ev = pd.concat(rows, ignore_index=True)
    ev["code4"] = ev["code"].str[:4]
    ev["ts"] = pd.to_datetime(ev["date"] + " " + ev["time"], errors="coerce")
    ev = ev.dropna(subset=["ts"])
    # 場中（前場 09:00-11:25 / 後場 12:30-15:00）のみ。直後 5 バー（25 分）を追える時刻まで
    t = ev["ts"].dt.time
    in_session = ((t >= pd.Timestamp("09:00").time()) & (t <= pd.Timestamp("11:25").time())) | \
                 ((t >= pd.Timestamp("12:30").time()) & (t <= pd.Timestamp("15:00").time()))
    ev = ev[in_session & ev["code4"].isin(close.columns)]
    ev["is_kessan"] = ev["title"].str.contains("決算短信|業績予想|配当予想", na=False)

    bars = close.index
    drift_rows = []
    for _, e in ev.iterrows():
        code = e["code4"]
        # 開示直後の最初のバー境界
        pos = bars.searchsorted(e["ts"])
        if pos + 6 >= len(bars) or pos < 1:
            continue
        # 同じ日のバーか確認
        if bars[pos].date() != e["ts"].date() or bars[pos + 6].date() != e["ts"].date():
            continue
        c0 = close[code].iloc[pos]
        seq = close[code].iloc[pos:pos + 7] / c0 - 1
        if seq.isna().any():
            continue
        drift_rows.append({
            "code": code, "ts": e["ts"], "is_kessan": bool(e["is_kessan"]),
            **{f"t+{i}": float(seq.iloc[i]) for i in range(7)},
            "abs30": float(abs(seq.iloc[6])),
        })
    dd = pd.DataFrame(drift_rows)
    dd.to_parquet(OUT_DIR / "exp5_event_drift.parquet")

    # ベースライン: 全バー 30 分（6 バー）変化の絶対値
    base_abs = float(ret[uni].rolling(6).sum().abs().stack().median())
    res = {}
    for label, sub in [("決算系", dd[dd.is_kessan]), ("その他開示", dd[~dd.is_kessan])]:
        if len(sub) == 0:
            continue
        res[label] = {
            "events": int(len(sub)),
            "mean_t1_bps": round(float(sub["t+1"].mean()) * 1e4, 1),
            "mean_t6_bps": round(float(sub["t+6"].mean()) * 1e4, 1),
            "median_abs30_bps": round(float(sub["abs30"].median()) * 1e4, 1),
            # 初動と同方向に乗る戦略: t+1 の符号 → t+1→t+6 を保有
            "momentum_after_1bar_bps": round(float(
                (np.sign(sub["t+1"]) * (sub["t+6"] - sub["t+1"])).mean()) * 1e4, 1),
        }
    res["baseline_median_abs30_bps"] = round(base_abs * 1e4, 1)
    return res


# ── main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    close, vol = build_cache()
    uni = pick_universe(close, vol)
    print(f"[universe] 流動性上位 {len(uni)} 銘柄")
    ret = bar_returns(close)

    results = {}
    results["exp1_seasonality"] = exp1_seasonality(ret, uni)
    print("[ok] exp1 シーズナリティ")
    results["exp2_gap"] = exp2_gap(close, uni)
    print("[ok] exp2 寄りギャップ")
    results["exp3_momentum_mr"] = exp3_momentum(ret, uni)
    print("[ok] exp3 モメンタム/平均回帰")
    results["exp4_leadlag"] = exp4_leadlag(ret)
    print("[ok] exp4 リードラグ")
    results["exp5_event_drift"] = exp5_event_drift(close, ret, uni)
    print("[ok] exp5 場中開示ドリフト")

    out = OUT_DIR / "results_summary.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved -> {out}")
