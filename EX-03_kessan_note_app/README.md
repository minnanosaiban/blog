# 番外編: 決算 JSON から Note 記事プロンプトを生成

連載記事: [番外編：決算データで「Note記事の下書き」を作る ― XBRL→プロンプト生成アプリ](https://minnanosaiban.github.io/hotline/blog/posts/EX-03_kessan_note_app/)

決算短信・有報の XBRL を統一 JSON に変換し、銘柄コードを入力するだけで **Note 記事の下書きプロンプト**を生成する Streamlit アプリです。
データ変換のしくみは連載 1-3 [決算 XBRL を JSON に変換](https://minnanosaiban.github.io/hotline/blog/posts/01-03_xbrl_to_json/) と共通です。

![決算 Note プロンプト生成アプリ](app.png)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `app.py` | Streamlit アプリ | 決算 JSON から Note 記事の下書きプロンプトを生成 |
| `fetch_kessan.py` | 決算短信 XBRL 取得 | TDnet から決算短信 XBRL を取得 |
| `fetch_yuho.py` | 有報 XBRL 取得 | EDINET から有報 XBRL を取得 |

## セットアップ

```bash
# このリポジトリは連載全体の 1 フォルダです
git clone https://github.com/minnanosaiban/blog.git
cd blog/EX-03_kessan_note_app

# 依存パッケージをインストール
pip install -r requirements.txt

# 決算 Note プロンプト生成アプリを起動
streamlit run app.py
```

## 使い方

1. `fetch_yuho.py`（有報・EDINET）または `fetch_kessan.py`（決算短信・TDnet）で XBRL を取得 → `data/xbrl/` に保存
2. アプリ起動時に自動で `data/json/` へ変換（下記「データの用意」の ⚠️ を必ず確認）
3. 銘柄コードを入力・期を選択し、着目点を一言メモ → プロンプトを生成
4. Claude などの AI に貼り付けて下書きを作成

## データの用意

```
data/
├── xbrl/   ← 決算短信 ZIP / 有報 ZIP を配置（fetch_kessan.py / fetch_yuho.py が自動保存）
└── json/   ← アプリ起動時に自動変換（再配布禁止）
```

> **⚠️ XBRL → JSON 変換について**: 変換処理は著者環境のパーサー（`collectors`）に依存します。これが無い環境では変換は動きません。その場合は **事前変換済みの JSON を `data/json/` に直接置く**ことでアプリは動作します。

> **再配布制限**: EDINET / TDnet の開示データは提供元の規約により再配布禁止です。

## ライセンス / 免責

ソースコードは MIT ライセンスです。データは各提供元の規約に従ってください。  
投資判断は自己責任でお願いします。
