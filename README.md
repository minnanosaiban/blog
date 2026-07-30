# 株 × Python × ML ― ブログ連載アプリ＆スクリプト集

[株 × Python × ML](https://minnanosaiban.github.io/hotline/blog/) ブログ連載で紹介した分析を、ローカルで動く Streamlit アプリ／図表生成スクリプトとして実装したものです。

連載は **3 フェーズ＋番外編** で構成され、各フォルダの番号は連載の読む順（`フェーズ-連番`、例 `01-01_…`）に対応しています。

## 連載との対応

| 連載 | 記事 | フォルダ | 種別 | 内容 |
|---|---|---|---|---|
| 1-1 | [まず、「株価」を取得する](https://minnanosaiban.github.io/hotline/blog/posts/01-01_get_stock_prices/) | [`01-01_chart_5min/`](./01-01_chart_5min/) | アプリ | 5分足ローソク＋騰落率テーブル |
| 1-2 | [決算データを無料で集める](https://minnanosaiban.github.io/hotline/blog/posts/01-02_collect_other_data/) | [`01-02_1_chart_multi/`](./01-02_1_chart_multi/) | アプリ | 複数銘柄カードグリッド（90日チャート＋PER/PBR/配当） |
| 1-2 | 〃 | [`01-02_2_chart_earnings_pattern/`](./01-02_2_chart_earnings_pattern/) | アプリ | 決算パターングリッド（発表後の値動きを5分類） |
| 1-3 | [決算 XBRL を JSON に変換](https://minnanosaiban.github.io/hotline/blog/posts/01-03_xbrl_to_json/) | [`01-03_xbrl_json/`](./01-03_xbrl_json/) | アプリ＋図 | XBRL → JSON 変換 ＋ CFマトリクス比較 |
| 2-1 | [4象限で GARP を見る](https://minnanosaiban.github.io/hotline/blog/posts/02-01_garp_peg_roe/) | [`02-01_PEG_ROE/`](./02-01_PEG_ROE/) | アプリ＋図 | PEG × ROE GARP スクリーナー |
| 2-2 | [マルチファクタースコア](https://minnanosaiban.github.io/hotline/blog/posts/02-02_multifactor_scoreboard/) | [`02-02_multifactor/`](./02-02_multifactor/) | アプリ＋図 | マルチファクター・スコアボード |
| 2-3 | [アクルーアル分析](https://minnanosaiban.github.io/hotline/blog/posts/02-03_accrual_analysis/) | [`02-03_accrual/`](./02-03_accrual/) | 図 | 利益の質（アクルーアル）分析 |
| 2-4 | [コンセンサス予想を検証](https://minnanosaiban.github.io/hotline/blog/posts/02-04_triangulation/) | [`02-04_triangulation/`](./02-04_triangulation/) | 図 | 会社予想の三角測量（トライアンギュレーション） |
| 2-5 | [セグメント分析](https://minnanosaiban.github.io/hotline/blog/posts/02-05_segment_analysis/) | [`02-05_segments/`](./02-05_segments/) | 図 | 事業セグメント別の収益分析 |
| 2-6 | [コングロマリット・ディスカウント](https://minnanosaiban.github.io/hotline/blog/posts/02-06_segment_core_stocks/) | （`02-05_segments/` の図を流用） | 図 | 総合商社の事業転換＋ＥＮＥＯＳ ピークアウト |
| 2-7 | [CARで見る「決算の効き」](https://minnanosaiban.github.io/hotline/blog/posts/02-07_narrative_car/) | [`02-07_car/`](./02-07_car/) | 図 | CAR（累積異常リターン）イベントスタディ |
| 2-8 | [EVで見る「会社の値段」](https://minnanosaiban.github.io/hotline/blog/posts/02-08_enterprise_value/) | [`02-08_enterprise_value/`](./02-08_enterprise_value/) | 図 | 企業価値（EV）／EV・営業CF 分析 |
| 3-1 | [コサイン類似度](https://minnanosaiban.github.io/hotline/blog/posts/03-01_similar_earnings_search/) | [`03-01_similarity/`](./03-01_similarity/) | 分析＋図 | 決算の「似たもの」検索（コサイン類似度） |
| 3-2 | [K-NN 分類](https://minnanosaiban.github.io/hotline/blog/posts/03-02_knn_prediction/) | [`03-02_knn/`](./03-02_knn/) | 分析＋図 | K-NN による決算後値動きの分類 |
| 3-3 | [K-means クラスタリング](https://minnanosaiban.github.io/hotline/blog/posts/03-03_earnings_clustering/) | [`03-03_clustering/`](./03-03_clustering/) | 分析＋図 | 決算プロファイルの K-means クラスタリング |
| 3-4 | [ランダムフォレスト](https://minnanosaiban.github.io/hotline/blog/posts/03-04_random_forest/) | [`03-04_random_forest/`](./03-04_random_forest/) | 分析＋図 | ランダムフォレストと特徴量重要度 |
| 3-5 | [階層型クラスタリング](https://minnanosaiban.github.io/hotline/blog/posts/03-05_price_clustering/) | [`03-05_price_clustering/`](./03-05_price_clustering/) | 図 | 値動きの階層型クラスタリング |
| 3-6 | [PCA 異常検知](https://minnanosaiban.github.io/hotline/blog/posts/03-06_price_anomaly/) | [`03-06_price_anomaly/`](./03-06_price_anomaly/) | 図 | PCA による共動崩壊の異常検知 |
| EX-1 | [超短期の統計検証](https://minnanosaiban.github.io/hotline/blog/posts/EX-01_intraday_stats/) | [`EX-01_intraday_stats/`](./EX-01_intraday_stats/) | 分析＋図 | 5分足での超短期アノマリーの統計検証 |
| EX-2 | [超短期の ML 検証](https://minnanosaiban.github.io/hotline/blog/posts/EX-02_intraday_ml/) | [`EX-02_intraday_ml/`](./EX-02_intraday_ml/) | 分析＋図 | 5分足での超短期予測の機械学習検証 |
| EX-3 | [決算データで Note 記事の下書きを作る](https://minnanosaiban.github.io/hotline/blog/posts/EX-03_kessan_note_app/) | [`EX-03_kessan_note_app/`](./EX-03_kessan_note_app/) | アプリ | 決算 JSON から Note 記事プロンプトを生成 |

> **種別について** ― 初期の連載（1-1〜2-2）は `app.py` で動く Streamlit アプリ、2-3 以降は記事の図表を再生成するスクリプト（`*_make_images.py` / `analysis.py` / `thumb.py`）です。

## セットアップ

### アプリ系（1-1〜2-2）

各フォルダで個別に依存関係をインストールします。

```bash
cd 01-01_chart_5min   # または 01-02_1_chart_multi など
pip install -r requirements.txt
streamlit run app.py
```

### 図表生成スクリプト系（2-3〜EX-2）

記事に掲載した図を再生成するスクリプトです。`pandas` / `matplotlib` などが必要で、株価・決算データは別途取得しておく必要があります（下記「データについて」）。

```bash
cd 02-03_accrual
python 06_accrual_make_images.py   # analysis.py を持つフォルダは先に分析を実行
```

詳細な手順は各フォルダの README を参照してください。

## データについて

本リポジトリには **コードのみ** を公開しています。
株価・決算データ・業績指標は提供元の利用規約により再配布できません。
各アプリ／スクリプトの README に取得方法を記載しています。

## データ時点と再現性（AS_OF）

図表は **2026-05-31 時点**で取得できたデータを使って生成しています。`*_make_images.py` / `analysis.py` の各ファイル冒頭に基準日の定数があり、

```python
AS_OF = "2026-05-31"   # この日付以前のデータだけを使って図を生成する
```

別の時点で作り直したい場合は、この `AS_OF` を変更して再実行してください（株価・決算データは別途取得しておく必要があります）。

- **有報・決算短信について** ― `AS_OF` は会計期末ではなく**提出日（filing_date）**で切ります。3月期末でも6月提出の有報などは「5/31 時点では未取得」として除外されます。
- **楽天（rakunav）データについて** ― 楽天データは日付列の無いスナップショットのため、図は 2026-05-31 時点に取得した CSV で生成しています。後から最新の楽天データを取得しても本リポジトリの図とは一致しません（楽天データは提供元規約により再配布もできません）。
- **CAR（2-7 / 3-1）について** ― CAR（累積異常リターン）は、2026-05-31 時点で収集できた範囲のデータで算出しています。そのため発表が5月末に近いイベントの一部は、決算後 `[-1, +20]` 営業日の窓がまだ埋まりきっておらず、未完了のまま掲載しています。
- **インタラクティブアプリ（1-1〜2-2）について** ― `app.py` で動くアプリは固定していません。実行時に最新データを取得するため、表示される数値は記事中の図（2026-05-31 時点）とは異なります。
- **5分足（1-1 / EX）について** ― 5分足データは取得元の保持期間が約60日と短く、後から 2026-05-31 時点を取り直すことはできません（日足は期間指定で再現可能です）。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。
投資判断は自己責任でお願いします。
