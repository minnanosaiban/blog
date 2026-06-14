# 株 × Python × ML ― ブログ連載アプリ＆スクリプト集

[株 × Python × ML](https://minnanosaiban.github.io/hotline/blog/) ブログ連載で紹介した分析を、ローカルで動く Streamlit アプリ／図表生成スクリプトとして実装したものです。

連載は **3 フェーズ＋番外編** で構成され、各フォルダの番号は記事番号（`NN_…`）に対応しています。

## 連載との対応

| 連載 | 記事 | フォルダ | 種別 | 内容 |
|---|---|---|---|---|
| 1-1 | [まず、「株価」を取得する](https://minnanosaiban.github.io/hotline/blog/posts/01_get_stock_prices/) | [`01_chart_5min/`](./01_chart_5min/) | アプリ | 5分足ローソク＋騰落率テーブル |
| 1-2 | [決算データを無料で集める](https://minnanosaiban.github.io/hotline/blog/posts/02_collect_other_data/) | [`02_1_chart_multi/`](./02_1_chart_multi/) | アプリ | 複数銘柄カードグリッド（90日チャート＋PER/PBR/配当） |
| 1-2 | 〃 | [`02_2_chart_earnings_pattern/`](./02_2_chart_earnings_pattern/) | アプリ | 決算パターングリッド（発表後の値動きを5分類） |
| 1-3 | [決算 XBRL を JSON に変換](https://minnanosaiban.github.io/hotline/blog/posts/03_xbrl_to_json/) | [`03_xbrl_json/`](./03_xbrl_json/) | アプリ＋図 | XBRL → JSON 変換 ＋ 記事プロンプト生成 |
| 2-1 | [4象限で GARP を見る](https://minnanosaiban.github.io/hotline/blog/posts/04_garp_peg_roe/) | [`04_PEG_ROE/`](./04_PEG_ROE/) | アプリ＋図 | PEG × ROE GARP スクリーナー |
| 2-2 | [マルチファクタースコア](https://minnanosaiban.github.io/hotline/blog/posts/05_multifactor_scoreboard/) | [`05_multifactor/`](./05_multifactor/) | アプリ＋図 | マルチファクター・スコアボード |
| 2-3 | [アクルーアル分析](https://minnanosaiban.github.io/hotline/blog/posts/06_accrual_analysis/) | [`06_accrual/`](./06_accrual/) | 図 | 利益の質（アクルーアル）分析 |
| 2-4 | [コンセンサス予想を検証](https://minnanosaiban.github.io/hotline/blog/posts/07_triangulation/) | [`07_triangulation/`](./07_triangulation/) | 図 | 会社予想の三角測量（トライアンギュレーション） |
| 2-5 | [セグメント分析](https://minnanosaiban.github.io/hotline/blog/posts/08_segment_analysis/) | [`08_segments/`](./08_segments/) | 図 | 事業セグメント別の収益分析 |
| 2-6 | [コングロマリット・ディスカウント](https://minnanosaiban.github.io/hotline/blog/posts/08b_segment_core_stocks/) | （`08_segments/` の図を流用） | 図 | 総合商社の事業転換＋ＥＮＥＯＳ ピークアウト |
| 2-7 | [CARで見る「決算の効き」](https://minnanosaiban.github.io/hotline/blog/posts/09b_narrative_car/) | [`09_car/`](./09_car/) | 図 | CAR（累積異常リターン）イベントスタディ |
| 2-8 | [EVで見る「会社の値段」](https://minnanosaiban.github.io/hotline/blog/posts/18_enterprise_value/) | [`18_enterprise_value/`](./18_enterprise_value/) | 図 | 企業価値（EV）／EV・営業CF 分析 |
| 3-1 | [コサイン類似度](https://minnanosaiban.github.io/hotline/blog/posts/10_similar_earnings_search/) | [`10_similarity/`](./10_similarity/) | 分析＋図 | 決算の「似たもの」検索（コサイン類似度） |
| 3-2 | [K-NN 分類](https://minnanosaiban.github.io/hotline/blog/posts/11_knn_prediction/) | [`11_knn/`](./11_knn/) | 分析＋図 | K-NN による決算後値動きの分類 |
| 3-3 | [K-means クラスタリング](https://minnanosaiban.github.io/hotline/blog/posts/12_earnings_clustering/) | [`12_clustering/`](./12_clustering/) | 分析＋図 | 決算プロファイルの K-means クラスタリング |
| 3-4 | [ランダムフォレスト](https://minnanosaiban.github.io/hotline/blog/posts/13_random_forest/) | [`13_random_forest/`](./13_random_forest/) | 分析＋図 | ランダムフォレストと特徴量重要度 |
| 3-5 | [階層型クラスタリング](https://minnanosaiban.github.io/hotline/blog/posts/14_price_clustering/) | [`14_price_clustering/`](./14_price_clustering/) | 図 | 値動きの階層型クラスタリング |
| 3-6 | [PCA 異常検知](https://minnanosaiban.github.io/hotline/blog/posts/15_price_anomaly/) | [`15_price_anomaly/`](./15_price_anomaly/) | 図 | PCA による共動崩壊の異常検知 |
| EX-1 | [超短期の統計検証](https://minnanosaiban.github.io/hotline/blog/posts/16_intraday_stats/) | [`16_intraday_stats/`](./16_intraday_stats/) | 分析＋図 | 5分足での超短期アノマリーの統計検証 |
| EX-2 | [超短期の ML 検証](https://minnanosaiban.github.io/hotline/blog/posts/17_intraday_ml/) | [`17_intraday_ml/`](./17_intraday_ml/) | 分析＋図 | 5分足での超短期予測の機械学習検証 |

> **種別について** ― 初期の連載（01〜05）は `app.py` で動く Streamlit アプリ、06 以降は記事の図表を再生成するスクリプト（`*_make_images.py` / `analysis.py` / `thumb.py`）です。

## セットアップ

### アプリ系（01〜05）

各フォルダで個別に依存関係をインストールします。

```bash
cd 01_chart_5min   # または 02_1_chart_multi など
pip install -r requirements.txt
streamlit run app.py
```

### 図表生成スクリプト系（06〜18）

記事に掲載した図を再生成するスクリプトです。`pandas` / `matplotlib` などが必要で、株価・決算データは別途取得しておく必要があります（下記「データについて」）。

```bash
cd 06_accrual
python 06_accrual_make_images.py   # analysis.py を持つフォルダは先に分析を実行
```

詳細な手順は各フォルダの README を参照してください。

## データについて

本リポジトリには **コードのみ** を公開しています。
株価・決算データ・業績指標は提供元の利用規約により再配布できません。
各アプリ／スクリプトの README に取得方法を記載しています。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。
投資判断は自己責任でお願いします。
