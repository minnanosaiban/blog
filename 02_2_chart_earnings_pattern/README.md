# 連載チャート02-2: 決算パターングリッド

連載記事: [株価以外も取得しよう ― EDINET・TDnet・証券会社のアプリを活用](https://minnanosaiban.github.io/hotline/blog/2026/05/19/02_collect_other_data/)

決算発表後の値動きを「上げ / 逆V字 / 無風 / V字 / 下げ」の5パターンに分類し、  
4列カードグリッドで表示する Streamlit アプリです。  
各カードに5分足エリアチャートと発表時刻の縦線を表示します。

![app](app.png)

## ファイル

| ファイル | 内容 |
|---|---|
| `app.py` | メインアプリ |
| `fetch_prices.py` | yfinance で株価を取得して parquet に保存 |
| `fetch_tdnet.py` | TDnet から決算発表日時を取得して earnings.csv を生成 |
| `build_earnings.py` | ローカルの TDnet CSV から earnings.csv を生成（著者環境用） |

## セットアップ

```bash
pip install -r requirements.txt
streamlit run app.py
```

初回起動時はメイン画面に Step 1 / Step 2 の手順が表示されます。

## データの用意

### Step 1: 株価データ（yfinance）

アプリ内「⬛ データ取得」→「株価データ」→ **「株価を取得」** を押してください。

保存先:
- `data/prices/daily/{コード}.parquet`（日足）
- `data/prices/5min/{コード}.parquet`（5分足）

> **再配布制限**: Yahoo Finance のデータは利用規約により再配布禁止です。

### Step 2: 決算発表日時（TDnet から自動取得）

アプリ内「⬛ データ取得」→「決算日時」→ 日付レンジを設定して **「TDnet から取得」** を押してください。  
TDnet（東証適時開示サービス）から決算短信の発表日時を自動取得し `earnings.csv` を生成します。

**日付レンジの目安:**
- 3月期決算（5月発表）→ `2026-05-01` 〜 `2026-05-31`
- 9月期決算（11月発表）→ `2026-11-01` 〜 `2026-11-30`

> **再配布制限**: TDnet の開示データは提供元の規約により再配布禁止です。

### 東証 銘柄一覧（data_j.xls）

TOPIX500 フィルタに使用します。

1. [JPX 公式](https://www.jpx.co.jp/markets/statistics-equities/misc/01.html) から「東証上場銘柄一覧」をダウンロード
2. `data/master/data_j.xls` に保存

> **再配布制限**: JPX が著作権を保有するデータのため再配布禁止です。

### 銘柄短縮名（stocks.csv）

`data/master/stocks.csv` はリポジトリに同梱（著者作成・再配布可）。

## パターン分類のしきい値

| パラメータ | 値 | 意味 |
|---|---|---|
| `DAYS_BEFORE` | 1 | チャート表示の発表前営業日数 |
| `DAYS_AFTER` | 3 | チャート表示の発表後営業日数 |
| `TH_FIRST` | 2.0% | 初日リターンの flat 判定閾値 |
| `TH_FINAL` | 3.0% | 最終リターンの flat 判定閾値 |

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。  
投資判断は自己責任でお願いします。
