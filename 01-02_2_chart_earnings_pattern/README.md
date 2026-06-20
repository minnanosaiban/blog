# 連載 1-2: 決算データを無料で集める（決算パターングリッド）

連載記事: [決算データを無料で集める ― EDINET・TDnet の公式 XBRL を活用](https://minnanosaiban.github.io/hotline/blog/posts/01-02_collect_other_data/)

決算発表後の値動きを「上げ / 逆V字 / 無風 / V字 / 下げ」の5パターンに分類し、  
4列カードグリッドで表示する Streamlit アプリです。  
各カードに5分足エリアチャートと発表時刻の縦線を表示します。

![app](app.png)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `app.py` | Streamlit アプリ | メインアプリ |
| `fetch_prices.py` | 株価取得 | yfinance で株価を取得して parquet に保存 |
| `fetch_tdnet.py` | 決算日時取得 | TDnet から決算発表日時を取得して earnings.csv を生成 |
| `build_earnings.py` | データ整形 | ローカルの TDnet CSV から earnings.csv を生成（著者環境用） |

## セットアップ

```bash
# このリポジトリは連載全体の 1 フォルダです
git clone https://github.com/minnanosaiban/blog.git
cd blog/01-02_2_chart_earnings_pattern

# 依存パッケージをインストールして起動
pip install -r requirements.txt
streamlit run app.py
```

初回起動時はメイン画面に Step 1 / Step 2 の手順が表示されます。続けて下記「データの用意」を参照してください。

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

### 銘柄名

銘柄名は **`data_j.xls`（JPX 公式「東証上場銘柄一覧」）の「銘柄名」列** から表示します。上の手順で data_j.xls を置けば、そのまま名前が出ます（追加準備は不要）。

#### （任意）短縮名でコンパクトに見せたい場合

JPX の正式名称は長め（ホールディングス名・投資信託名など）で、一覧では折り返して読みづらくなりがちです。**短い表示名**で見栄えよく並べたいときは、自分で短縮名リストを作ると効果的です。

1. [トレーダーズ・ウェブ 株価一覧](https://www.traders.co.jp/market_jp/stock_list/price/all/all/1) を開く
2. 「コード」「銘柄名」をコピーし、`コード,銘柄` の2列で `data/master/stocks.csv` に保存
3. `stocks.csv` があれば、JPX 正式名より **こちらの短縮名が優先表示** されます

> **再配布について**: この短縮名リストは提供元（トレーダーズ・ウェブ）のデータのため、本リポジトリには同梱していません。各自でご用意ください。

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
