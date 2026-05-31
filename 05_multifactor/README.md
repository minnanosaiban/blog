# 連載02: マルチファクター・スコアボード

7 ファクター（Value / Quality / Growth / Consensus / Sentiment / Momentum / Risk）でレーダーチャート採点する銘柄分析ツールです。

連載記事: [マルチファクターで銘柄を採点する ― スコアボードで「全方位優等生」を発見する](https://minnanosaiban.github.io/hotline/blog/2026/05/20/02_multifactor_scoreboard/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `app.py` | Streamlit アプリ | インタラクティブダッシュボード |
| `05_multifactor_make_images.py` | Matplotlib チャート生成 | 記事用チャート画像（スコアボード・レーダー・散布図）を PNG 出力 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- **株価データ (yfinance)**: Yahoo Finance の利用規約により、取得したデータの再配布はできません。
- **証券会社が提供する銘柄情報 (CSV)**: 個人利用を前提としたサービスのため、CSV データを再配布することはできません。

読者の方は各自のアカウント・環境でデータを取得してご利用ください。

## セットアップ

```bash
pip install -r requirements.txt
```

## 起動

```bash
streamlit run app.py
```

## 動作環境

`app.py` は `C:\stock_analysis` 配下の以下を読み込みます:

- rakunav CSV 14 指標（113 EPS実績 / 215 BPS予 / 141 配当金 / 133 EV/EBITDA / 118 ROE / 119 ROA / 125 営業利益率 / 130 自己資本比率 / 122 売上変化率 / 129 経常変化率 / 219 3年成長率(予) / 220 業績予想修正率 / 221 経常変化率(予) / 120 時価総額）
- yfinance 日足 parquet（utils/price_metrics 経由で 出来高・値上り率・ボラ・β 等を計算）
- TOPIX 500 銘柄リスト（utils/universe_topix500 経由）

別環境で動かす場合は、データ取得部 (`RAKUNAV_SPECS` 周辺、`load_price_metrics`) をご自身の環境に合わせて書き換えてください。

## スコア定義

- 各指標を **TOPIX 500 内パーセンタイルランク化（0-100）**
- ファクター毎に指標スコアの単純平均
- 総合スコア = 7 ファクター平均
- **70 以上が上位 30% の注目候補**（連載02 記事と統一）

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
