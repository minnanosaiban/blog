# 連載 3-6: PCA 異常検知

「市場・同業は動いていないのに、その銘柄だけ突発的に上げ下げした日」を検出するツールです。買収・TOB・業績修正・事故など個別材料が出た銘柄のトリアージで、3-2 の個別ショック検出器を決算に依らない毎日・全銘柄版にしたもの。予測ではなく検出です。

連載記事: [PCA 異常検知 ― 値動きの「共動の崩れ」で突発材料を検出](https://minnanosaiban.github.io/hotline/blog/posts/03-06_price_anomaly/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `15_price_anomaly_make_images.py` | 分析＋チャート生成 | PCA（10 主成分）で共動成分をモデル化し、残差から異常日を検出。記事用 PNG を出力 |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

生成画像: `00_thumbnail` / `01_mechanism`（仕組み）/ `02_event_casestudy`（イベント事例）/ `03_sudden_events`（突発材料）/ `04_eneos_decoupling`（ＥＮＥＯＳのデカップリング）/ `05_daily_monitor`（日次モニタ）

## 手法

- 直近 **500 営業日**の日次終値リターン（カバレッジ 95% 以上）を **PCA（10 主成分）** で共動成分に分解
- 共動で説明できない **残差の大きさ**を異常スコアとし、市場・同業と乖離した日を検出
- ＥＮＥＯＳの「共動の崩れ」を時系列で可視化

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません
- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet`・`data/prices/stocks/daily/<code>.parquet`・`data/master/sectors/*.csv`）を前提とし、`scipy` / `scikit-learn` が必要です。出力 PNG はパス直書きで hotline の `docs/blog/posts/img/03-06_price_anomaly/` に書き込みます。別環境ではスクリプト冒頭のパス定数をご自身の環境に合わせて書き換えてください。`15_price_anomaly_make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
