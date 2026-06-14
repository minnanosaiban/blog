# 連載 1-1: まず、「株価」を取得する

連載記事: [まず、「株価」を取得する ― yfinance から parquet 保存、チャート、自作アプリまで](https://minnanosaiban.github.io/hotline/blog/posts/01-01_get_stock_prices/)

複数銘柄の5分足ローソクチャートと騰落率テーブルを並べて表示する Streamlit アプリです。

![app](app.png)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `app.py` | Streamlit アプリ | メインアプリ。ローカル parquet から読み込み |
| `app_simple.py` | Streamlit アプリ | **おまけ**。株価のダウンロード不要。ひとつの pyファイルでチャートを表示できます |
| `fetch_prices.py` | 株価取得 | yfinance で株価を取得して parquet に保存 |

## セットアップ

```bash
# このリポジトリは連載全体の 1 フォルダです
git clone https://github.com/minnanosaiban/blog.git
cd blog/01-01_chart_5min

# 依存パッケージをインストールして起動
pip install -r requirements.txt
streamlit run app.py
```

初回起動時はメイン画面に手順が表示されます。続けて下記「データの用意」を参照してください。

> 💡 株価をまだ貯めていなくても **とりあえずチャートが見たい** ときは、おまけの `streamlit run app_simple.py`（yfinance から直接取得）が手軽です。

## データの用意

### 株価データ（yfinance）

アプリ内「⬛ データ取得」→「データ取得」を開き、**「株価を取得」** を押してください。

保存先:
- `data/prices/daily/{コード}.parquet`（日足）
- `data/prices/5min/{コード}.parquet`（5分足）

> **再配布制限**: Yahoo Finance のデータは利用規約により再配布禁止です。

### 東証 銘柄一覧（data_j.xls）

TOPIX500 フィルタに使用します。

1. [JPX 公式](https://www.jpx.co.jp/markets/statistics-equities/misc/01.html) から「東証上場銘柄一覧」をダウンロード
2. `data/master/data_j.xls` に保存

> **再配布制限**: JPX が著作権を保有するデータのため再配布禁止です。

### 銘柄短縮名（stocks.csv）

`data/master/stocks.csv` はリポジトリに同梱（著者作成・再配布可）。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。  
投資判断は自己責任でお願いします。
