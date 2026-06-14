"""
連載15 類似決算検索 ― 数値特徴量ベクトル + コサイン類似度

実 embedding API は呼ばない。決算短信 JSON から 10 次元の数値特徴量を抽出し、
z-score 正規化 → cosine similarity で「似た決算」を発見する。

出力:
  data/blog15/features.parquet         : 全銘柄 × 特徴量行列
  data/blog15/similarity_marubeni.csv  : 丸紅 2026/3 通期の類似 Top-15
  data/blog15/similarity_sojitz.csv    : 双日 2026/3 通期の類似 Top-15
  data/blog15/similarity_with_car.csv  : 上記を連載13 events.parquet と join
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STATEMENTS = ROOT / "data" / "statements"
EVENTS = ROOT / "data" / "blog13" / "events.parquet"
OUT_DIR = ROOT / "data" / "blog15"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "net_sales_yoy",      # 売上 YoY %
    "operating_yoy",      # 営業利益 YoY %
    "pretax_yoy",         # 税引前利益 YoY %
    "net_income_yoy",     # 純利益 YoY %
    "comprehensive_yoy",  # 包括利益 YoY %
    "div_growth_pct",     # 配当成長率 %
    "op_margin",          # 営業利益率 %
    "net_margin",         # 純利益率 %
    "segment_count",      # セグメント数
    "max_seg_share",      # 最大セグメント売上構成比 %
]


def extract_features(d: dict) -> dict | None:
    m = d.get("metadata", {}) or {}
    if m.get("kind") != "actual":
        return None
    perf = d.get("performance", {}) or {}
    cur = perf.get("current", {}) or {}
    cp  = perf.get("change_pct", {}) or {}
    div = d.get("dividend", {}) or {}
    dprev = (div.get("actual_prior")   or {}).get("annual")
    dcur  = (div.get("actual_current") or {}).get("annual")
    segs  = (d.get("segments", {}) or {}).get("current", []) or []

    ns = cur.get("net_sales")
    oi = cur.get("operating_income")
    ni = cur.get("net_income")

    # 営業利益率 / 純利益率
    op_margin  = (oi / ns * 100) if (ns and oi is not None and ns > 0) else None
    net_margin = (ni / ns * 100) if (ns and ni is not None and ns > 0) else None

    # 配当成長率
    div_growth = None
    if dprev and dcur and dprev > 0:
        div_growth = (dcur - dprev) / dprev * 100

    # セグメント
    seg_sales = [(s.get("net_sales") or s.get("external_revenue") or s.get("total_revenue"))
                 for s in segs]
    seg_sales = [s for s in seg_sales if isinstance(s, (int, float)) and s > 0]
    seg_count = len(seg_sales)
    max_share = (max(seg_sales) / sum(seg_sales) * 100) if seg_sales else None

    feat = {
        "code":             str(m.get("code", "")),
        "company":          m.get("company_name", ""),
        "period_end":       m.get("fiscal_year_end") or m.get("period_end"),
        "period_type":      m.get("period_type", ""),
        "filing_date":      m.get("filing_date"),
        "net_sales_yoy":    cp.get("net_sales"),
        "operating_yoy":    cp.get("operating_income"),
        "pretax_yoy":       cp.get("profit_before_tax"),
        "net_income_yoy":   cp.get("net_income"),
        "comprehensive_yoy": cp.get("comprehensive_income"),
        "div_growth_pct":   div_growth,
        "op_margin":        op_margin,
        "net_margin":       net_margin,
        "segment_count":    seg_count,
        "max_seg_share":    max_share,
    }
    return feat


def load_features() -> pd.DataFrame:
    rows = []
    for f in STATEMENTS.glob("*_FY.json"):
        if "forecast" in f.name:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        feat = extract_features(d)
        if feat:
            rows.append(feat)
    df = pd.DataFrame(rows)
    return df


def normalize(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        s = out[c]
        # clip 外れ値（±300% で頭打ち）
        s = s.clip(lower=-300, upper=300)
        med = s.median()
        std = s.std()
        if std and std > 0:
            out[c] = (s - med) / std
        else:
            out[c] = 0
    return out


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_top_k(df_z: pd.DataFrame, query_code: str, query_fyend: str, k: int = 15) -> pd.DataFrame:
    mask = (df_z["code"] == query_code) & (df_z["period_end"] == query_fyend)
    if not mask.any():
        return pd.DataFrame()
    qrow = df_z[mask].iloc[0]
    qvec = qrow[FEATURE_COLS].to_numpy(dtype=float)
    others = df_z[~mask].copy()
    feats = others[FEATURE_COLS].to_numpy(dtype=float)
    # NaN を 0 に補完（特徴量欠損を「平均的」として扱う）
    qvec = np.nan_to_num(qvec)
    feats = np.nan_to_num(feats)
    sims = []
    for v in feats:
        sims.append(cosine_similarity(qvec, v))
    others["similarity"] = sims
    return others.sort_values("similarity", ascending=False).head(k)


def main():
    print("=== 1) Load features ===")
    df = load_features()
    print(f"  {len(df)} statements with kind=actual")
    print(f"  non-null features:\n{df[FEATURE_COLS].notna().sum()}")
    df.to_parquet(OUT_DIR / "features.parquet")

    print("=== 2) Normalize (z-score) ===")
    df_z = normalize(df, FEATURE_COLS)

    print("=== 3) Top-15 similar to 丸紅 2026/3 通期 ===")
    sim_m = find_top_k(df_z, "8002", "2026-03-31", k=15)
    cols_view = ["code", "company", "period_end", "similarity"] + FEATURE_COLS
    sim_m_view = df.merge(sim_m[["code", "period_end", "similarity"]],
                          on=["code", "period_end"], how="inner")
    sim_m_view = sim_m_view.sort_values("similarity", ascending=False)
    sim_m_view.to_csv(OUT_DIR / "similarity_marubeni.csv", index=False, encoding="utf-8-sig")
    print(sim_m_view[["code", "company", "period_end", "similarity",
                      "net_sales_yoy", "net_income_yoy", "div_growth_pct"]].to_string())

    print("=== 4) Top-15 similar to 双日 2026/3 通期 ===")
    sim_s = find_top_k(df_z, "2768", "2026-03-31", k=15)
    sim_s_view = df.merge(sim_s[["code", "period_end", "similarity"]],
                          on=["code", "period_end"], how="inner")
    sim_s_view = sim_s_view.sort_values("similarity", ascending=False)
    sim_s_view.to_csv(OUT_DIR / "similarity_sojitz.csv", index=False, encoding="utf-8-sig")
    print(sim_s_view[["code", "company", "period_end", "similarity",
                      "net_sales_yoy", "net_income_yoy", "div_growth_pct"]].head(10).to_string())

    print("=== 4b) Top-15 similar to ＥＮＥＯＳ 2026/3 通期 ===")
    sim_e = find_top_k(df_z, "5020", "2026-03-31", k=15)
    sim_e_view = df.merge(sim_e[["code", "period_end", "similarity"]],
                          on=["code", "period_end"], how="inner")
    sim_e_view = sim_e_view.sort_values("similarity", ascending=False)
    sim_e_view.to_csv(OUT_DIR / "similarity_eneos.csv", index=False, encoding="utf-8-sig")
    try:
        print(sim_e_view[["code", "company", "period_end", "similarity",
                          "net_sales_yoy", "net_income_yoy", "div_growth_pct"]].head(10).to_string())
    except UnicodeEncodeError:
        # Windows cp932 で表示できない文字（NBSP 等）がある場合は CSV のみ出力
        print(f"  (表示省略: similarity_eneos.csv に {len(sim_e_view)} 行出力済)")

    print("=== 5) Compute ad-hoc CAR for 2026/3 期 announcements ===")
    # 2026/3 期 announce は events.parquet に未収録のため、tdnet ログ + 株価で
    # short window CAR ([-1,+1], [-1,+5]) を ad-hoc 計算。[-1,+20] は 2026-05-21 時点で未完了
    from datetime import time as dtime
    tdnet_dir = ROOT / "data" / "news" / "tdnet"
    prices_dir = ROOT / "data" / "prices" / "stocks" / "daily"
    macro_dir  = ROOT / "data" / "prices" / "macro" / "daily"

    # Load TOPIX
    topix = pd.read_parquet(macro_dir / "TOPIX.parquet")
    topix.index = pd.to_datetime(topix.index)
    trading_days = topix.index.normalize().drop_duplicates().sort_values()

    # Load 2026-04, 2026-05 TDnet 決算短信ログ
    tdnet_rows = []
    for ym in ["2026-04", "2026-05"]:
        for f in sorted(tdnet_dir.glob(f"{ym}-*.csv")):
            try:
                df_t = pd.read_csv(f, encoding="utf-8-sig", dtype={"code": str})
            except Exception:
                continue
            df_t = df_t.dropna(subset=["code", "time", "title"])
            df_t = df_t[df_t["title"].astype(str).str.contains("決算短信", na=False)]
            df_t["code"] = df_t["code"].astype(str).str.strip()
            df_t["date"] = pd.to_datetime(df_t["date"], errors="coerce").dt.date
            tdnet_rows.append(df_t)
    if tdnet_rows:
        tdnet_kessan = pd.concat(tdnet_rows, ignore_index=True)
    else:
        tdnet_kessan = pd.DataFrame()
    print(f"  tdnet 2026-04~05 kessan rows: {len(tdnet_kessan)}")

    def _t0(date_val, time_str):
        try:
            t = pd.to_datetime(time_str).time()
        except Exception:
            return None
        base = pd.Timestamp(date_val)
        if t >= dtime(15, 0):
            idx = trading_days.searchsorted(base)
            if idx >= len(trading_days): return None
            if trading_days[idx] == base: idx += 1
            if idx >= len(trading_days): return None
            return trading_days[idx]
        else:
            idx = trading_days.searchsorted(base)
            if idx >= len(trading_days): return None
            return trading_days[idx]

    def _car_short(code, t0, hi):
        f = prices_dir / f"{code}.parquet"
        if not f.exists(): return None
        sd = pd.read_parquet(f)
        sd.index = pd.to_datetime(sd.index)
        if "ret_pct" not in sd.columns:
            sd["ret_pct"] = sd["Close"].pct_change() * 100
        merged = sd[["ret_pct"]].join(topix["chg_pct"].rename("topix_pct"), how="inner")
        if t0 not in merged.index: return None
        pos = merged.index.get_loc(t0)
        lo = pos - 1
        hi_idx = pos + hi
        if lo < 0 or hi_idx >= len(merged): return None
        sub = merged.iloc[lo:hi_idx + 1]
        abn = sub["ret_pct"] - sub["topix_pct"]
        if abn.isna().any(): return None
        return float(abn.sum())

    def _normalize_code(c):
        """TSE 5桁コード(8002→80020)を4桁に正規化。'135A0'→'135A' のような英数字コードも対応。"""
        s = str(c).strip()
        if len(s) == 5:
            return s[:4]
        return s

    car2026_rows = []
    for _, ev in tdnet_kessan.iterrows():
        t0 = _t0(ev["date"], str(ev["time"]))
        if t0 is None: continue
        code4 = _normalize_code(ev["code"])
        car2026_rows.append({
            "code": code4, "date": ev["date"], "time": ev["time"],
            "t0": t0,
            "car_m1_p1": _car_short(code4, t0, 1),
            "car_m1_p5": _car_short(code4, t0, 5),
        })
    car2026 = pd.DataFrame(car2026_rows)
    print(f"  computed CAR for {len(car2026)} 2026 events")
    car2026.to_parquet(OUT_DIR / "events_2026.parquet")

    # Join with similarity view
    # similarity_view の code を str に統一して join
    car2026["code"] = car2026["code"].astype(str)
    for label, sim_view in [("marubeni", sim_m_view), ("sojitz", sim_s_view), ("eneos", sim_e_view)]:
        sv = sim_view.copy()
        sv["code"] = sv["code"].astype(str)
        joined = sv.merge(
            car2026[["code", "car_m1_p1", "car_m1_p5"]].groupby("code").mean().reset_index(),
            on="code", how="left")
        joined.to_csv(OUT_DIR / f"similarity_with_car_{label}.csv",
                      index=False, encoding="utf-8-sig")
        avg = joined[["car_m1_p1", "car_m1_p5"]].mean()
        n = joined["car_m1_p1"].notna().sum()
        print(f"  [{label}] n_with_car={n}/{len(joined)}, "
              f"avg [-1,+1]={avg.get('car_m1_p1'):+.2f}, [-1,+5]={avg.get('car_m1_p5'):+.2f}")
        wr = (joined["car_m1_p5"] > 0).sum() / max(1, joined["car_m1_p5"].notna().sum()) * 100
        print(f"  [{label}] [-1,+5] 勝率 = {wr:.1f}% (n={joined['car_m1_p5'].notna().sum()})")

    print("=== DONE ===")


if __name__ == "__main__":
    main()
