"""
5分足・日足を yfinance で取得して parquet に保存・追記する（連載01）。

- 日足  : 長期（既定 2 年）→ data/prices/stocks/daily/{コード}.parquet
- 5分足 : 直近約 60 日（yfinance の上限）→ data/prices/stocks/5min/{コード}.parquet
- 既存ファイルがあれば連結し、同一時刻の重複を落として追記
- 株式分割をさかのぼって調整する auto_adjust=True を既定

使い方:
    pip install -r requirements.txt
    python fetch_prices.py 5020 5019 5021   # 銘柄コードを並べる
    python fetch_prices.py                   # 引数なしなら CODES の既定値

※ 取得した株価データ（parquet）は提供元の規約により再配布しないでください。
   本リポジトリの data/ 配下は空のプレースホルダです。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# 既定の銘柄（石油元売3社）。コマンドライン引数で上書き可
CODES = ["5020", "5019", "5021"]

DATA_DIR  = Path(__file__).resolve().parent / "data" / "prices"
DIR_5MIN  = DATA_DIR / "5min"
DIR_DAILY = DATA_DIR / "daily"


def _merge_save(path: Path, new: pd.DataFrame) -> int:
    """既存 parquet に連結し、重複（同一インデックス）を落として保存。保存後の行数を返す。"""
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


def fetch_one(code: str, period_daily: str = "2y", period_5min: str = "60d") -> None:
    symbol = f"{code}.T"

    df_d = yf.download(symbol, period=period_daily, interval="1d",
                       auto_adjust=True, progress=False)
    df_5 = yf.download(symbol, period=period_5min, interval="5m",
                       auto_adjust=True, progress=False)

    # yfinance が MultiIndex で返すケースに対応
    for d in (df_d, df_5):
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)

    n_d = _merge_save(DIR_DAILY / f"{code}.parquet", df_d)
    n_5 = _merge_save(DIR_5MIN / f"{code}.parquet", df_5)
    print(f"{code}: 日足 {n_d} 行 / 5分足 {n_5} 行")


def main() -> None:
    codes = sys.argv[1:] or CODES
    for c in codes:
        try:
            fetch_one(c)
        except Exception as e:
            print(f"{c}: 取得失敗 ― {e}")


if __name__ == "__main__":
    main()
