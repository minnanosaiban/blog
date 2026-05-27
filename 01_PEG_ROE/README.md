# 連載01: GARP スクリーナー

PEG × ROE で「成長と割安の両立」を発掘する GARP（Growth At a Reasonable Price）スクリーナーです。

連載記事: [PEG × ROE で「成長と割安の両立銘柄」を発掘する ― GARP の理論と実践](https://minnanosaiban.github.io/hotline/blog/2026/05/20/01_garp_peg_roe/)

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

- **証券会社が提供する銘柄情報 (rakunav CSV)**: 個人利用を前提としたサービスのため、CSV データを再配布することはできません。

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

`app.py` は `C:\stock_analysis` 配下の rakunav CSV（118 ROE / 113 EPS実績 / 213 EPS予想 / 120 時価総額）を読み込む構成になっています。別環境で動かす場合は、データ取得部 (`RAKUNAV_SPECS` 周辺) をご自身の環境に合わせて書き換えてください。

## しきい値

GARP の理想ゾーンを `PEG ≤ 1.0 AND ROE ≥ 10%` で固定しています（連載01 記事と統一）。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
