# 連載 3-4: ランダムフォレスト

ランダムフォレストで決算 10 指標から CAR の方向（上 / 下）を予測し、**精度は多数派ベースライン未満**（＝当たらない）こと、そして **impurity 重要度と permutation 重要度が食い違う「重要度の罠」** を実証するツールです。

連載記事: [ランダムフォレスト ― 予測は失敗、「特徴量重要度」の落とし穴を学ぶ](https://minnanosaiban.github.io/hotline/blog/posts/03-04_random_forest/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `analysis.py` | 分析 | RF 分類・5-fold 交差検証・ホールドアウト・impurity / permutation 重要度・ベースライン比較 |
| `make_images.py` | チャート生成 | 記事用 PNG（精度 vs ベースライン・AUC・重要度の 2 つの測り方） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません
- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet`・`events_2026.parquet`）を前提としています。`scikit-learn` が必要です。別環境では `analysis.py` のパス・データ取得部をご自身の環境に合わせて書き換えてください。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
