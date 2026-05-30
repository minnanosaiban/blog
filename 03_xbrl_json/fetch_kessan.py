"""
決算短信 iXBRL ダウンロード (TDnet)

TDnet 適時開示一覧から「決算短信」の iXBRL ファイルを取得し
data/xbrl/ に保存します。

使い方:
    python fetch_kessan.py --code 5020 --date 2026-05-14
    python fetch_kessan.py --code 5020           # 直近営業日を対象
    python fetch_kessan.py --code 5020 --start-date 2026-05-01 --end-date 2026-05-31

保存先: data/xbrl/{doc_id}.htm  （app.py が自動で JSON へ変換します）

注意:
    TDnet は公開 API を提供していないためスクレイピングで取得します。
    短時間に大量リクエストを送らないよう SLEEP_SEC を設けています。
"""
from __future__ import annotations

import argparse
import datetime
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TDNET_BASE  = "https://www.release.tdnet.info/inbs/"
OUT_DIR     = Path(__file__).parent / "data" / "xbrl"
SLEEP_SEC   = 1.0
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _latest_business_day() -> datetime.date:
    d = datetime.date.today()
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d


def _business_days(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def fetch_doc_list(date_str: str) -> list[dict]:
    """指定日の TDnet 開示一覧を全ページ取得。"""
    raw_date = date_str.replace("-", "")
    records, page = [], 1
    while True:
        url = TDNET_BASE + f"I_list_{page:03d}_{raw_date}.html"
        try:
            resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
            resp.encoding = "utf-8"
        except requests.RequestException as e:
            print(f"  [ERR] {url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr")
        found = 0
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            t    = cols[0].get_text(strip=True)
            code = cols[1].get_text(strip=True)
            titl = cols[3].get_text(strip=True)
            if not (len(t) == 5 and t[2] == ":"):
                continue
            a = cols[3].find("a") or row.find("a")
            href = a["href"] if a and a.get("href") else ""
            records.append({"date": date_str, "time": t, "code": code,
                            "title": titl, "href": href})
            found += 1

        if not found:
            break
        page += 1
        time.sleep(SLEEP_SEC)

    return records


def _to_4digit(code: str) -> str:
    c = code.strip()
    return c[:4] if len(c) == 5 and c.endswith("0") else c


def _pdf_href_to_xbrl_url(href: str) -> str | None:
    """
    TDnet の PDF href から XBRL ZIP URL を生成する。
    PDF:  1401{YYYYMMDDNNNNNN}.pdf
    XBRL: 0812{YYYYMMDDNNNNNN}.zip  （先頭4桁を置換）
    """
    filename = href.rsplit("/", 1)[-1]
    if not filename.startswith("1401") or not filename.endswith(".pdf"):
        return None
    doc_num = filename[4:-4]   # YYYYMMDDNNNNNN
    return TDNET_BASE + "0812" + doc_num + ".zip"


def download_xbrl_zip(href: str, out_path: Path) -> bool:
    """TDnet の PDF href から XBRL ZIP を取得して保存する。"""
    url = _pdf_href_to_xbrl_url(href)
    if not url:
        print(f"    [SKIP] XBRL URL を生成できません（PDF リンク形式が想定外）: {href}")
        return False
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 1000:
            save_path = out_path.with_suffix(".zip")
            save_path.write_bytes(resp.content)
            print(f"    保存: {save_path.name} ({len(resp.content):,} bytes)")
            return True
        print(f"    [WARN] HTTP {resp.status_code} / {len(resp.content)} bytes: {url}")
    except requests.RequestException as e:
        print(f"    [ERR] {e}")
    return False


def run(code: str, dates: list[datetime.date]) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_code = code.strip()
    fetched = 0

    for d in dates:
        date_str = d.isoformat()
        print(f"\n--- {date_str} ---")
        records = fetch_doc_list(date_str)
        for r in records:
            if _to_4digit(r["code"]) != target_code:
                continue
            if "決算短信" not in r["title"]:
                continue
            if "訂正" in r["title"]:
                continue
            print(f"  対象: {r['time']} {r['title']}")
            m = re.search(r"(\d{18,})", r["href"])
            if not m:
                continue
            doc_id = m.group(1)
            base = OUT_DIR / doc_id
            if list(OUT_DIR.glob(f"{doc_id}*")):
                print(f"    [SKIP] 既存")
                continue
            ok = download_xbrl_zip(r["href"], base)
            if ok:
                fetched += 1
            else:
                print(f"    [WARN] XBRL ZIP を取得できませんでした")

    print(f"\n取得完了: {fetched} 件 → {OUT_DIR}")
    return fetched


def main() -> None:
    parser = argparse.ArgumentParser(description="TDnet 決算短信 iXBRL ダウンロード")
    parser.add_argument("--code",       required=True, help="銘柄コード (例: 5020)")
    parser.add_argument("--date",       default=None,  help="取得日 YYYY-MM-DD")
    parser.add_argument("--start-date", default=None,  help="範囲開始 YYYY-MM-DD")
    parser.add_argument("--end-date",   default=None,  help="範囲終了 YYYY-MM-DD")
    args = parser.parse_args()

    if args.start_date and args.end_date:
        dates = _business_days(
            datetime.date.fromisoformat(args.start_date),
            datetime.date.fromisoformat(args.end_date),
        )
    elif args.date:
        dates = [datetime.date.fromisoformat(args.date)]
    else:
        dates = [_latest_business_day()]

    run(args.code, dates)


if __name__ == "__main__":
    main()
