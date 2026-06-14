# 連載 2-1: 4象限で GARP を見る

PEG × ROE で「成長と割安の両立」を発掘する GARP（Growth At a Reasonable Price）スクリーナーです。

連載記事: [4象限で GARP を見る ― 「成長と割安の両立」銘柄を探す](https://minnanosaiban.github.io/hotline/blog/posts/04_garp_peg_roe/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `app.py` | Streamlit アプリ | インタラクティブダッシュボード |
| `04_PEG_ROE_make_images.py` | Matplotlib チャート生成 | 記事用チャート画像（GARP マップ・テーブル・株価チャート）を PNG 出力 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- **証券会社が提供する銘柄情報**: 個人利用を前提としたサービスのため、CSV データを再配布することはできません。

読者の方は各自のアカウント・環境でデータを取得してご利用ください。

## セットアップ

```bash
pip install -r requirements.txt
```

## 起動

**Streamlit アプリ**（インタラクティブダッシュボード）:
```bash
streamlit run app.py
```

**チャート画像生成スクリプト**（Matplotlib で PNG 出力）:
```bash
python 04_PEG_ROE_make_images.py
```

## 動作環境

両スクリプトとも `C:\stock_analysis` 配下の CSV（118 ROE / 113 EPS実績 / 213 EPS予想 / 120 時価総額）と、執筆者ローカルのユーティリティモジュール（`config.paths` / `utils.master_names` 等）を読み込む構成になっています。別環境で動かす場合は、データ取得部 (`RAKUNAV_SPECS` 周辺) と yfinance や証券会社が無料で提供しているデータを使ってご自身の環境に合わせてください。コード構造をテンプレートとして参考にしていただければと思います。

## しきい値

GARP の理想ゾーンを `PEG ≤ 1.0 AND ROE ≥ 10%` で固定しています（連載 2-1 記事と統一）。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
