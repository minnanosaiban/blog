# 連載 3-1: コサイン類似度

10 次元の数値特徴量とコサイン類似度で「似た決算」を検索し、類似群の CAR とクエリ銘柄自身の CAR の乖離から「個別ショック」を発見するツールです。

連載記事: [コサイン類似度 ― 「似ている決算」を数値で検索する](https://minnanosaiban.github.io/hotline/blog/posts/10_similar_earnings_search/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `analysis.py` | 分析 | 決算 JSON → 10 次元特徴量抽出・z-score 正規化・コサイン類似度・2026/3 期 ad-hoc CAR |
| `make_images.py` | チャート生成 | 記事用 PNG（パイプライン図・PCA 投影・類似 Top-15・CAR 分布・数値 vs LLM 比較） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません
- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet` 等）を前提としています。別環境では `analysis.py` のパス・データ取得部をご自身の環境に合わせて書き換えてください。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
