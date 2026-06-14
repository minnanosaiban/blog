# 連載 2-8: EVで見る「会社の値段」

元売3社・総合商社8社・資源2社の計13社を EV（企業価値）と簡易 DCF で分析するツールです。

連載記事: [EVで見る「会社の値段」 ― 元売・商社・資源 13社を簡易DCFで検証](https://minnanosaiban.github.io/hotline/blog/posts/18_enterprise_value/)

## ファイル

| ファイル | 種別 | 内容 |
|---|---|---|
| `make_images.py` | チャート生成 | 記事用 PNG 3枚（EV 構成・EV/営業CF 倍率・簡易 DCF vs 市場 EV） |
| `thumb.py` | サムネイル生成 | 記事サムネ（00_thumbnail.png） |
| `_blog_style.py` | 共通スタイル | matplotlib の rcParams と一定幅保存 |

## 分析の枠組み

- **EV = 時価総額 + ネットデット**（有利子負債 − 現金）。有価証券報告書 XBRL から有利子負債・現金・キャッシュフローを抽出
- **EV/営業CF**: 商社は損益計算書に営業利益を表示しないため EV/EBITDA が定義できない。13社共通で使える営業 CF で代替
- **簡易 DCF**: FCF（営業 CF + 投資 CF）÷ 割引率 7%（g = 0 の永続価値）を市場 EV と比較
- 株式数は決算短信（2026年3月期）、なければ有報 BPS 逆算。株式分割（伊藤忠5倍・兼松2倍・コスモエネ2倍）を補正

### 対象 13 社

| グループ | コード | 会社名 |
|---|---|---|
| 元売 | 5020 / 5019 / 5021 | ＥＮＥＯＳ / 出光興産 / コスモエネＨＤ |
| 総合商社 | 8001 / 8031 / 8058 / 8053 / 8002 / 8015 / 8020 / 2768 | 伊藤忠 / 三井物産 / 三菱商事 / 住友商事 / 丸紅 / 豊田通商 / 兼松 / 双日 |
| 資源 | 1605 / 1662 | ＩＮＰＥＸ / 石油資源開発 |

## データについて

本リポジトリには **コードのみ** を公開しています。データは同梱していません。

必要なデータと想定パス（`C:\stock_analysis\` 配下）:

| データ | パス | 取得方法 |
|---|---|---|
| 有報 JSON | `data/yuho/<EDINET_ID>/<EDINET_ID>_*.json` | EDINET XBRL を `collectors/parse_yuho_xbrl.py` で変換 |
| 決算短信 JSON | `data/statements/<code>_2026-03-31_FY.json` | 決算短信 XBRL を独自パーサで変換 |
| 株価 parquet | `data/prices/stocks/daily/<code>.parquet` | yfinance で取得（Yahoo Finance 規約により再配布不可） |
| 株式分割マスタ | `data/master/stock_splits.csv` | 手動管理（有報 BPS 逆算を補正するため） |

## 動作環境

```
python >= 3.10
numpy, pandas, matplotlib
```

スクリプトは `C:\stock_analysis` 配下のデータ構成を前提としています。`make_images.py` は同フォルダの `_blog_style.py` を読み込みます。データパスは `make_images.py` 冒頭の定数（`YUHO` / `STMTS` / `PRICES` / `SPLITS`）を環境に合わせて書き換えてください。

## ライセンス / 免責

本コードは学習・参考用途で公開しています。投資判断は自己責任でお願いします。
