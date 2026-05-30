# 株 × Python × AI ― ブログ連載アプリ集

[株 × Python × AI](https://minnanosaiban.github.io/hotline/blog/) ブログ連載で紹介した分析を、ローカルで動く Streamlit アプリとして実装したものです。

## アプリ一覧

| フォルダ | 連載記事 | 内容 |
|---|---|---|
| [`01_chart_5min/`](./01_chart_5min/) | [連載チャート01](https://minnanosaiban.github.io/hotline/blog/2026/05/18/01_get_stock_prices/) | 5分足ローソク＋騰落率テーブル |
| [`02_1_chart_multi/`](./02_1_chart_multi/) | [連載チャート02-1](https://minnanosaiban.github.io/hotline/blog/2026/05/19/02_collect_other_data/) | 複数銘柄カードグリッド（90日チャート＋PER/PBR/配当） |
| [`02_2_chart_earnings_pattern/`](./02_2_chart_earnings_pattern/) | [連載チャート02-2](https://minnanosaiban.github.io/hotline/blog/2026/05/19/02_collect_other_data/) | 決算パターングリッド（発表後の値動きを5分類） |
| [`03_xbrl_json/`](./03_xbrl_json/) | [連載03](https://minnanosaiban.github.io/hotline/blog/2026/05/20/03_xbrl_to_json/) | XBRL → JSON 変換 ＋ Note 記事プロンプト生成 |
| [`04_PEG_ROE/`](./04_PEG_ROE/) | [連載04](https://minnanosaiban.github.io/hotline/blog/2026/05/20/01_garp_peg_roe/) | PEG × ROE GARP スクリーナー |
| [`05_multifactor/`](./05_multifactor/) | [連載05](https://minnanosaiban.github.io/hotline/blog/2026/05/20/02_multifactor_scoreboard/) | マルチファクター・スコアボード |
| [`06_eps_revision/`](./06_eps_revision/) | [連載06](https://minnanosaiban.github.io/hotline/blog/2026/05/20/03_eps_revision_momentum/) | EPS リビジョン・モメンタム散布図 |
| [`07_surprise/`](./07_surprise/) | [連載07](https://minnanosaiban.github.io/hotline/blog/2026/05/20/04_surprise_scoreboard/) | 連続サプライズ・スコアボード |

## セットアップ

各フォルダで個別に依存関係をインストールします。

```bash
cd 01_chart_5min   # または他のフォルダ
pip install -r requirements.txt
streamlit run app.py
```

詳細な手順は各フォルダの README を参照してください。

## データについて

本リポジトリには **コードのみ** を公開しています。  
株価・決算データ・業績指標は提供元の利用規約により再配布できません。  
各アプリの README に取得方法を記載しています。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。  
投資判断は自己責任でお願いします。
