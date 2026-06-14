"""
番外編A 追加検証: ユーザー仮説の条件付きパターン 2 本。

  expA  連続 k 本上昇（下落）した直後の次バーは逆に動くか（k=2..6）
  expB  寄りギャップが閾値（±0.5/1/2/3%）を超えた日の寄り後 30 分は逆に動くか

blog20 のキャッシュを再利用。IN（〜2026-03-31）/ OUT（2026-04-01〜）で安定性も見る。
出力: data/blog20/conditional_patterns.json
実行: python scripts/blog20b_conditional_patterns.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\stock_analysis")
CACHE = ROOT / "data" / "blog20"
IN_END = pd.Timestamp("2026-03-31")
COSTS_BP = [5, 10]
UNIVERSE_N = 300
MIN_DAYS = 100


def load() -> tuple[pd.DataFrame, list[str]]:
    close = pd.read_parquet(CACHE / "close_wide.parquet")
    vol = pd.read_parquet(CACHE / "volume_wide.parquet")
    turnover = (close * vol).groupby(close.index.date).sum()
    days_ok = (close.notna().groupby(close.index.date).any()).sum() >= MIN_DAYS
    med = turnover[days_ok.index[days_ok]].median()
    uni = med.nlargest(UNIVERSE_N).index.tolist()
    return close, uni


def run_lengths(flag: np.ndarray) -> np.ndarray:
    """flag (bars × stocks) の「直前から連続 True の長さ」。"""
    out = np.zeros(flag.shape, dtype=np.int16)
    acc = np.zeros(flag.shape[1], dtype=np.int16)
    for t in range(flag.shape[0]):
        acc = np.where(flag[t], acc + 1, 0)
        out[t] = acc
    return out


def stats(per_trade: np.ndarray) -> dict:
    if len(per_trade) == 0:
        return {"trades": 0}
    m = float(per_trade.mean())
    return {
        "trades": int(len(per_trade)),
        "hit": round(float((per_trade > 0).mean()), 4),
        "per_trade_bps": round(m * 1e4, 2),
        "net_bps": {f"{c}bp": round(m * 1e4 - c, 2) for c in COSTS_BP},
    }


def main() -> None:
    close, uni = load()
    c = close[uni]
    dates = pd.Series(c.index.date, index=c.index)
    first_of_day = dates.ne(dates.shift())
    ret = c.pct_change(fill_method=None)
    ret[first_of_day.values] = np.nan

    is_in = np.asarray(c.index.normalize() <= IN_END)
    nxt = ret.shift(-1).values  # 次バー（翌日初バーは NaN なので日跨ぎは自動除外）

    results = {"expA_streak_reversal": {}, "expB_gap_threshold": {}}

    # ── expA: 連続 k 本の後を逆張り ─────────────────────────────────────────
    r = ret.values
    up_run = run_lengths(np.nan_to_num(r) > 0)
    dn_run = run_lengths(np.nan_to_num(r) < 0)
    for k in (2, 3, 4, 5, 6):
        for label, run, sign in [("up", up_run, -1.0), ("down", dn_run, +1.0)]:
            cond = (run >= k) & ~np.isnan(nxt)
            per = {}
            for split, msk in [("in", is_in[:, None]), ("out", ~is_in[:, None])]:
                m = cond & msk
                per[split] = stats(sign * nxt[m])
            results["expA_streak_reversal"][f"{k}連続{label} → 逆張り"] = per

    # ── expB: 寄りギャップ閾値 → 寄り後 30 分を逆張り ───────────────────────
    grp = c.groupby(dates.values)
    day_open = grp.first()
    day_close = grp.last()
    pos = grp.cumcount()
    c7 = c[(pos == 6).values].copy()
    c7.index = dates[(pos == 6).values].values
    day7 = c7.reindex(day_open.index)
    r30 = (day7 / day_open - 1).values
    gap = (day_open / day_close.shift(1) - 1).values
    days = pd.to_datetime(pd.Index(day_open.index))
    d_in = np.asarray(days <= IN_END)[:, None]

    ok = ~np.isnan(gap) & ~np.isnan(r30) & (np.abs(gap) < 0.15)
    for th in (0.005, 0.01, 0.02, 0.03):
        for label, cond, sign in [
            (f"ギャップ+{th:.1%}超 → 売り", ok & (gap > th), -1.0),
            (f"ギャップ−{th:.1%}超 → 買い", ok & (gap < -th), +1.0),
        ]:
            per = {}
            for split, msk in [("in", d_in), ("out", ~d_in)]:
                m = cond & msk
                per[split] = stats(sign * r30[m])
            results["expB_gap_threshold"][label] = per

    out = CACHE / "conditional_patterns.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
