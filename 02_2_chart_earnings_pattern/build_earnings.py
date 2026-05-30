"""
TDnet 適時開示 CSV → earnings.csv 生成スクリプト

data/news/tdnet/{date}.csv を走査し、タイトルに「決算短信」を含む行を抽出。
コードを 5桁→4桁に変換（末尾 0 を除去）して重複排除したうえで
C:/repos/blog/05_charts/earnings.csv に書き出す。

使い方:
    python build_earnings.py                              # 全 TDnet CSV を対象
    python build_earnings.py --start-date 2026-04-01     # 開始日指定
    python build_earnings.py --start-date 2026-04-01 --end-date 2026-05-31
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, r"C:\stock_analysis")

import pandas as pd

from config.paths import NEWS_TDNET

OUT_CSV = Path(__file__).parent / "earnings.csv"


def _to_4digit(code: str) -> str:
    """5桁末尾 0 → 4桁。それ以外はそのまま。"""
    c = str(code).strip()
    if len(c) == 5 and c.endswith("0"):
        return c[:4]
    return c


def load_tdnet_range(start: date | None, end: date | None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for p in sorted(NEWS_TDNET.glob("*.csv")):
        try:
            d = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        try:
            df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        except Exception as e:
            print(f"  [SKIP] {p.name}: {e}")
            continue
        if df.empty or "title" not in df.columns:
            continue
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build(start: date | None = None, end: date | None = None) -> None:
    print(f"=== earnings.csv 生成 ===")
    print(f"  TDnet dir : {NEWS_TDNET}")
    print(f"  期間      : {start or '全期間'} 〜 {end or '全期間'}")

    df = load_tdnet_range(start, end)
    if df.empty:
        print("  対象 CSV なし。終了。")
        return

    # 決算短信のみ抽出（訂正は除外）
    mask = (
        df["title"].str.contains("決算短信", na=False) &
        ~df["title"].str.startswith("（訂正）", na=False)
    )
    df = df[mask].copy()
    print(f"  決算短信 該当行: {len(df)} 件")

    # コード変換
    df["code"] = df["code"].map(_to_4digit)

    # 必要列だけ残す
    df = df[["date", "time", "code"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # 同一 (date, code) は最も早い時刻を採用
    df = (
        df.sort_values(["date", "code", "time"])
          .drop_duplicates(subset=["date", "code"], keep="first")
          .sort_values(["date", "code"])
          .reset_index(drop=True)
    )

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  出力: {OUT_CSV} ({len(df)} 件)")
    print("完了")


def main() -> None:
    parser = argparse.ArgumentParser(description="TDnet → earnings.csv 生成")
    parser.add_argument("--start-date", default=None, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end-date",   default=None, help="終了日 YYYY-MM-DD")
    args = parser.parse_args()

    start = date.fromisoformat(args.start_date) if args.start_date else None
    end   = date.fromisoformat(args.end_date)   if args.end_date   else None
    build(start, end)


if __name__ == "__main__":
    main()
