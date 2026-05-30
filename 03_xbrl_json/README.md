# 連載03 ― XBRL → JSON と 7年業績チャート

連載03「XBRL を JSON に変換して分析する」で使う、有報 JSON の業績時系列チャートアプリです。

## ファイル

| ファイル | 役割 |
|---|---|
| `app.py` | 有報 JSON から **純利益（棒）+ ROE（線）の 7 年チャート**を描く Streamlit アプリ。銘柄セレクタ・ピーク注釈つき |

## データの置き場所

```
data/yuho/{EDINETコード}/{...}.json   … 有報 JSON（XBRL → JSON 変換の出力）
```

**決算データ（JSON）は提供元の規約により再配布できません。** `data/yuho/` は空のプレースホルダ（`.gitkeep`）です。XBRL → JSON 変換でご自身の環境に生成してください（変換パーサーは公開準備中）。

各 JSON は次のキーを参照します：

- `metadata.fiscal_year_end` / `metadata.company_name`
- `financials.net_income`（純利益）/ `financials.roe`（ROE）

## 使い方

```bash
pip install -r requirements.txt
streamlit run app.py
```

銘柄セレクタで会社を選ぶと、純利益（黒字=緑 / 赤字=赤の棒）と ROE（右軸の線）が重なり、純利益ピークの年に注釈が付きます（既定は ＥＮＥＯＳ）。
