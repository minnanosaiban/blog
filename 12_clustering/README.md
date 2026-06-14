# 連載 3-3: K-means クラスタリング

k-means（教師なし学習）で決算 10 指標から「決算の型」を発見するツールです。シルエット係数で K=3 を選び、287 銘柄を「急回復・高成長／高収益・集中／平均・安定」の 3 型に分類します。

連載記事: [K-means クラスタリング ― 教師なし学習が分けた「決算の型」](https://minnanosaiban.github.io/hotline/blog/posts/12_earnings_clustering/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `analysis.py` | 分析 | 特徴量の z-score 正規化・シルエットによる K 決定・k-means・PCA 2D 投影・型ラベル付け |
| `make_images.py` | チャート生成 | 記事用 PNG（シルエット・型マップ・型プロファイル ヒートマップ） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 決算データ（EDINET / TDnet）: 提供元の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成（`data/blog15/features.parquet`）を前提としています。`scikit-learn` が必要です。別環境では `analysis.py` のパス・データ取得部をご自身の環境に合わせて書き換えてください。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
