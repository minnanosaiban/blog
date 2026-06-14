# 連載 3-5: 階層型クラスタリング

日次終値の相関から銘柄をデンドログラムでまとめ、「値動きが似た銘柄群」を業界地図として再現するツールです。予測ではなく記述・発見（3-2 / 3-4 の予測タスクとは別物）です。

連載記事: [階層型クラスタリング ― 値動きの相関で再現する業界地図](https://minnanosaiban.github.io/hotline/blog/posts/14_price_clustering/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `14_price_clustering_make_images.py` | 分析＋チャート生成 | 日次終値の相関行列・階層型クラスタリング（scipy linkage / fcluster）・MDS 銘柄マップ・ほぼ一致ペア抽出、記事用 PNG を出力 |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

生成画像: `00_thumbnail` / `01_corr_heatmap`（相関ヒートマップ）/ `02_stock_map`（MDS 銘柄マップ）/ `03_near_identical`（ほぼ一致ペア）

## 手法

- 直近 **500 営業日**の日次終値リターンで相関行列を作成（カバレッジ 95% 以上の銘柄）
- 相関距離（1 − ρ）で **階層型クラスタリング**し、12 クラスタに分割
- 相関 **ρ ≥ 0.90** の「ほぼ一致ペア」を抽出
- MDS で 2 次元に投影して銘柄マップを描画

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません
- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet`・`data/prices/stocks/daily/<code>.parquet`・`data/master/sectors/*.csv`）を前提とし、`scipy` / `scikit-learn` が必要です。出力 PNG はパス直書きで hotline の `docs/blog/posts/img/14_price_clustering/` に書き込みます。別環境ではスクリプト冒頭のパス定数をご自身の環境に合わせて書き換えてください。`14_price_clustering_make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
