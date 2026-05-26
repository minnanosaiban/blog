# 株 × Python × AI ― ブログ連載アプリ集

[株 × Python × AI](https://minnanosaiban.github.io/hotline/blog/) ブログ連載で紹介した分析を、ローカルで操作可能な Streamlit + Plotly アプリとして実装したものです。

## アプリ一覧

| 連載 | フォルダ | 内容 |
|---|---|---|
| 連載05 信用需給ダッシュボード | [`05_credit/`](./05_credit/) | 業績 × 需給 4 象限マトリクス |

## 起動

```powershell
cd 05_credit
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで http://localhost:8501 が開きます。

## データ

各アプリはローカル前提で `C:\stock_analysis` 配下の楽天 MS2 CSV を読みに行きます。Streamlit Cloud デプロイ時は `data/` にスナップショット CSV を同梱する形に切替予定。
