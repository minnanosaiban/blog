"""
TDnet 適時開示から決算短信の発表日時を取得して earnings.csv を生成する。

- URL: https://www.release.tdnet.info/inbs/I_list_{page}_{date}.html
- 「決算短信」を含み「（訂正）」で始まらないものを抽出
- 同一 (date, code) は最も早い時刻を採用

使い方:
    python fetch_tdnet.py --start-date 2026-04-01 --end-date 2026-05-31
"""
from __future__ import annotations

import argparse
import datetime
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

TDNET_BASE   = "https://www.release.tdnet.info/inbs/"
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}
SLEEP_SEC    = 0.5
OUT_CSV      = Path(__file__).parent / "earnings.csv"


def _to_4digit(code: str) -> str:
    c = str(code).strip()
    if len(c) == 5 and c.endswith("0"):
        return c[:4]
    return c


def fetch_one_page(date_str: str, page: int) -> list[dict]:
    raw_date = date_str.replace("-", "")
    url = TDNET_BASE + f"I_list_{page:03d}_{raw_date}.html"
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        resp.encoding = "utf-8"
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    records = []
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        t    = cols[0].get_text(strip=True)
        code = cols[1].get_text(strip=True)
        titl = cols[3].get_text(strip=True)
        if not (len(t) == 5 and t[2] == ":"):
            continue
        records.append({"date": date_str, "time": t, "code": code, "title": titl})
    return records


def fetch_tdnet_date(date_str: str) -> list[dict]:
    """指定日の TDnet 開示を全ページ取得して返す。"""
    all_records, page = [], 1
    while True:
        records = fetch_one_page(date_str, page)
        if not records:
            break
        all_records.extend(records)
        page += 1
        time.sleep(SLEEP_SEC)
    return all_records


def business_days(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days


def build_earnings(start: datetime.date, end: datetime.date,
                   progress_cb=None) -> pd.DataFrame:
    """
    指定期間の TDnet を走査して決算短信一覧を返す。
    progress_cb(i, total, date_str) を渡すと進捗コールバックが呼ばれる。
    """
    days = business_days(start, end)
    rows: list[dict] = []
    for i, d in enumerate(days):
        if progress_cb:
            progress_cb(i, len(days), d.isoformat())
        records = fetch_tdnet_date(d.isoformat())
        for r in records:
            if "決算短信" in r["title"] and not r["title"].startswith("（訂正）"):
                rows.append({"date": r["date"], "time": r["time"],
                             "code": _to_4digit(r["code"])})
    if not rows:
        return pd.DataFrame(columns=["date", "time", "code"])
    df = (pd.DataFrame(rows)
            .sort_values(["date", "code", "time"])
            .drop_duplicates(subset=["date", "code"], keep="first")
            .reset_index(drop=True))
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="TDnet → earnings.csv 生成")
    parser.add_argument("--start-date", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end-date",   required=True, help="終了日 YYYY-MM-DD")
    args = parser.parse_args()

    start = datetime.date.fromisoformat(args.start_date)
    end   = datetime.date.fromisoformat(args.end_date)
    days  = business_days(start, end)
    print(f"=== TDnet 取得（{start} 〜 {end}、{len(days)} 営業日）===")

    def cb(i, total, d): print(f"  [{i+1}/{total}] {d}")

    df = build_earnings(start, end, progress_cb=cb)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"完了: {len(df)} 件 → {OUT_CSV}")


if __name__ == "__main__":
    main()
