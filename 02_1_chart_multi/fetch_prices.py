"""
日足を yfinance で取得して parquet に保存・追記する（02_multi_chart 用）。

- 日足  : 長期（既定 2 年）→ data/prices/daily/{コード}.parquet
- 既存ファイルがあれば連結し、同一日付の重複を落として追記
- 株式分割をさかのぼって調整する auto_adjust=True を既定

使い方:
    python fetch_prices.py 8058 8031 8001
    python fetch_prices.py          # 引数なしなら CODES の既定値

※ 取得した株価データ（parquet）は提供元の規約により再配布しないでください。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

CODES = ["8058", "8031", "8001"]

DATA_DIR  = Path(__file__).resolve().parent / "data" / "prices"
DIR_DAILY = DATA_DIR / "daily"


def _merge_save(path: Path, new: pd.DataFrame) -> int:
    if new is None or new.empty:
        return 0
    if path.exists():
        merged = pd.concat([pd.read_parquet(path), new])
    else:
        merged = new
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(path)
    return len(merged)


def fetch_one(code: str, period_daily: str = "2y") -> None:
    symbol = f"{code}.T"
    df_d = yf.download(symbol, period=period_daily, interval="1d",
                       auto_adjust=True, progress=False)
    if isinstance(df_d.columns, pd.MultiIndex):
        df_d.columns = df_d.columns.get_level_values(0)
    n_d = _merge_save(DIR_DAILY / f"{code}.parquet", df_d)
    print(f"{code}: 日足 {n_d} 行")


def main() -> None:
    codes = sys.argv[1:] or CODES
    for c in codes:
        try:
            fetch_one(c)
        except Exception as e:
            print(f"{c}: 取得失敗 ― {e}")


if __name__ == "__main__":
    main()
