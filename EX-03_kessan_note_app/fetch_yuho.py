"""
有価証券報告書 XBRL ダウンロード (EDINET API v2)

EDINET API から有報（docTypeCode=120）の XBRL ZIP を取得し
data/xbrl/ に保存します。app.py が起動時に自動で JSON へ変換します。

使い方:
    python fetch_yuho.py --code 5020 --year 2025
    python fetch_yuho.py --edinet E24050 --year 2025
    python fetch_yuho.py --code 5020              # 直近 1 年分を探索

保存先: data/xbrl/{docID}.zip

EDINET API の仕様:
    https://disclosure.edinet-fsa.go.jp/
    ドキュメント一覧: GET /api/v2/documents.json?date=YYYY-MM-DD&type=2&Subscription-Key={key}
    書類ダウンロード: GET /api/v2/documents/{docID}?type=5&Subscription-Key={key}

APIキーの取得:
    https://disclosure.edinet-fsa.go.jp/ でユーザー登録後に発行。
    環境変数 EDINET_API_KEY または .env ファイルに設定してください。

注意:
    短時間に大量リクエストを送らないよう SLEEP_SEC を設けています。
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
import time
from pathlib import Path

import requests

# .env があれば読み込む
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

EDINET_BASE   = "https://disclosure.edinet-fsa.go.jp/api/v2"
OUT_DIR       = Path(__file__).parent / "data" / "xbrl"
SLEEP_SEC     = 0.5
HTTP_HEADERS  = {"User-Agent": "Mozilla/5.0"}
DOC_TYPE_YUHO = "120"   # 有価証券報告書


def _api_key() -> str:
    key = os.getenv("EDINET_API_KEY", "").strip()
    if not key:
        print("[error] EDINET_API_KEY が設定されていません。")
        print("        環境変数または .env ファイルに EDINET_API_KEY=<your_key> を追加してください。")
        sys.exit(1)
    return key


def _business_days(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def fetch_doc_list(date_str: str, key: str) -> list[dict]:
    """指定日の EDINET 提出書類一覧を取得（type=2: メタデータのみ）。"""
    url = f"{EDINET_BASE}/documents.json"
    params = {"date": date_str, "type": 2, "Subscription-Key": key}
    try:
        resp = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"  [ERR] {date_str}: {e}")
        return []


def download_zip(doc_id: str, out_path: Path, key: str) -> bool:
    """EDINET API type=5 で XBRL ZIP をダウンロードして保存。"""
    url = f"{EDINET_BASE}/documents/{doc_id}"
    params = {"type": 5, "Subscription-Key": key}
    try:
        resp = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=60)
        resp.raise_for_status()
        content = resp.content
        if len(content) < 1000:
            print(f"    [WARN] 応答が小さすぎます ({len(content)} bytes)")
            return False
        out_path.write_bytes(content)
        print(f"    保存: {out_path.name} ({len(content):,} bytes)")
        return True
    except Exception as e:
        print(f"    [ERR] {doc_id}: {e}")
        return False


def _to_4digit(sec_code: str) -> str:
    c = (sec_code or "").strip()
    return c[:4] if len(c) == 5 and c.endswith("0") else c


def run(code: str | None, edinet_code: str | None, year: int | None) -> int:
    key = _api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if year:
        start = datetime.date(year, 1, 1)
        end   = datetime.date(year, 12, 31)
    else:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=365)
        end   = today

    days = _business_days(start, end)
    print(f"探索期間: {start} 〜 {end} ({len(days)} 営業日)")
    fetched = 0

    for d in days:
        date_str = d.isoformat()
        docs = fetch_doc_list(date_str, key)
        time.sleep(SLEEP_SEC)

        for doc in docs:
            if doc.get("docTypeCode") != DOC_TYPE_YUHO:
                continue
            if code and _to_4digit(doc.get("secCode", "")) != code.strip():
                continue
            if edinet_code and doc.get("edinetCode", "") != edinet_code.strip():
                continue

            doc_id = doc.get("docID", "")
            print(f"\n  {date_str} | {doc.get('filerName', '')} | {doc_id}")

            out_path = OUT_DIR / f"{doc_id}.zip"
            if out_path.exists():
                print(f"    [SKIP] 既存")
                continue

            ok = download_zip(doc_id, out_path, key)
            if ok:
                fetched += 1
            time.sleep(SLEEP_SEC)

    print(f"\n取得完了: {fetched} 件 → {OUT_DIR}")
    return fetched


def main() -> None:
    parser = argparse.ArgumentParser(description="EDINET 有報 XBRL ダウンロード")
    parser.add_argument("--code",   default=None, help="銘柄コード 4桁 (例: 5020)")
    parser.add_argument("--edinet", default=None, help="EDINET コード (例: E24050)")
    parser.add_argument("--year",   type=int, default=None,
                        help="提出年 (例: 2026)。省略時は直近 1 年を探索")
    args = parser.parse_args()

    if not args.code and not args.edinet:
        parser.error("--code または --edinet を指定してください")

    run(code=args.code, edinet_code=args.edinet, year=args.year)


if __name__ == "__main__":
    main()
