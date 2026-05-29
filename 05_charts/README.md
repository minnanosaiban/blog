# 連載01・02 ― 株価チャートと取得スクリプト

連載01「まずは株価を取得しよう」と連載02「株価以外も取得しよう」で使った
チャートアプリ（Streamlit）と、株価取得スクリプトです。

## ファイル

| ファイル | 役割 | 連載 |
|---|---|---|
| `fetch_prices.py` | 5分足・日足を yfinance で取得して parquet に保存・追記 | 01 |
| `app1.py` | 5分足ローソク + 騰落率テーブル（複数銘柄）。Plotly | 01 |
| `app2.py` | 複数銘柄カードグリッド（PER/PBR/配当 + 90日チャート） | 02 |
| `app3.py` | 決算パターングリッド（発表後の値動きを5分類） | 02 |
| `earnings.csv` | app3 用の決算発表日時サンプル（date, time, code） | 02 |

## データの置き場所

```
data/prices/stocks/
├── 5min/     ← {コード}.parquet（5分足）。app3 が参照
└── daily/    ← {コード}.parquet（日足）
```

**生の株価データ（parquet）は提供元の規約により再配布できません。**
このリポジトリの `data/` は空のプレースホルダ（`.gitkeep`）です。
`fetch_prices.py` を実行すると、ご自身の環境で parquet が生成されます。

## 使い方

```bash
pip install -r requirements.txt

# データ取得（例: 石油元売3社）
python fetch_prices.py 5020 5019 5021

# チャートアプリ起動
streamlit run app1.py
```

- `app1.py` は yfinance から直接取得して表示するので、データ取得なしでも動きます。
- `app3.py` は `data/prices/stocks/5min/` の parquet を前提とします（先に `fetch_prices.py` を実行）。
- 株価指標 CSV（PER/PBR/配当）を使う `app2.py` は、証券会社が無料で提供する銘柄情報シートの
  CSV をご自身で用意してください（再配布不可のため同梱していません）。
