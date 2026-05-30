# 連載03: XBRL → JSON 変換と決算プロンプト生成

連載記事: [XBRL を JSON に変換して分析する ― 既存サービスにない切り口を作る](https://minnanosaiban.github.io/hotline/blog/2026/05/20/03_xbrl_to_json/)

XBRL（決算短信・有報）を統一 JSON に変換し、銘柄コードを指定するだけで Note 記事の下書きプロンプトを生成する Streamlit アプリです。

![app](app.png)

## ファイル

| ファイル | 内容 |
|---|---|
| `app.py` | メインアプリ。決算 JSON を読み込み Note 記事プロンプトを生成 |
| `fetch_kessan.py` | TDnet から決算短信 XBRL を取得 |
| `fetch_yuho.py` | EDINET から有報 XBRL を取得 |

## セットアップ

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 使い方

1. `fetch_kessan.py` または `fetch_yuho.py` で XBRL を取得 → `data/xbrl/` に保存
2. アプリ起動時に自動で `data/json/` へ変換
3. 銘柄コードを入力し、着目点を一言メモ → プロンプトを生成
4. Claude などの AI に貼り付けて下書きを作成

## データの用意

```
data/
├── xbrl/   ← 決算短信 ZIP または有報 ZIP を配置
└── json/   ← アプリ起動時に自動生成（再配布禁止）
```

> **再配布制限**: EDINET / TDnet の開示データは提供元の規約により再配布禁止です。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。  
投資判断は自己責任でお願いします。
