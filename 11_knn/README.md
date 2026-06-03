# 連載 3-2: K-NN 予測（個別ショック検出器）

K-NN 回帰で「類似決算群の CAR から自身の CAR を予測」を試み、**予測は失敗**（相関 r ≈ 0、ベースライン以下）する一方、**予測と実績の乖離が「個別ショック検出器」として機能する**ことを実証するツールです。

連載記事: [K-NN 回帰で「類似群からの値動き」を予測する](https://minnanosaiban.github.io/hotline/blog/posts/11_knn_prediction/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `analysis.py` | 分析 | K-NN（K=5/15/30）予測・精度（RMSE / 相関 / 方向一致率）・個別ショック抽出・ベースライン比較 |
| `make_images.py` | チャート生成 | 記事用 PNG（パイプライン図・予測 vs 実績・個別ショック Top-10・K 感度・戦略フロー） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません
- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet`・`events_2026.parquet` 等）を前提としています。別環境では `analysis.py` のパス・データ取得部をご自身の環境に合わせて書き換えてください。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
