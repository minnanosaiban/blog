# 番外編 EX-2: LightGBM で「次の5分」を当てられるか

5 分足の次バー方向（上 / 下）を LightGBM で分類し、AUC・的中率に加えて「確信度上位だけ取引した場合のコスト控除後損益」で評価するツールです。

連載記事: [LightGBM で「次の5分」を当てられるか ― 111万バーで検証](https://minnanosaiban.github.io/hotline/blog/posts/17_intraday_ml/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `analysis.py` | 分析 | 特徴量 8 個（直近リターン 4 本・ボラ・出来高 z・時間帯・ギャップ）の生成、パージ付き IN/OUT 分割、LightGBM 学習、確信度十分位分析 |
| `make_images.py` | チャート生成 | 記事用 PNG（十分位 × 次バーリターン・エッジ vs コスト） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## 検証の枠組み

- ラベルは「次の 5 分バーの上下」の 2 値分類。学習 111 万バー（〜2026-03-31）→ 検証 51 万バー（2026-04-01〜、境界 1 日はパージ）
- 評価は AUC・的中率に加え、**確信度トップ/ボトム 10% を取引した場合の 1 回あたり損益（コスト 5〜10bps 控除）** を主役にする
- 番外編 EX-1（`16_intraday_stats`）が生成する 5 分足キャッシュ（`data/blog20/close_wide.parquet` 等）を再利用する

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- 株価データ（yfinance）: Yahoo Finance の規約により再配布できません

## 動作環境

スクリプトは `C:\stock_analysis` 配下のデータ構成を前提としています。先に `16_intraday_stats/analysis.py` を実行してキャッシュを作ってください。LightGBM が無い環境では scikit-learn の HistGradientBoosting に自動でフォールバックします。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
