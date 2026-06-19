"""
連載03 Appendix: 決算XBRL → Note 記事プロンプト生成

- data/xbrl/ に決算短信（.htm/.zip）または有報（EDINET ZIP）を置く
- 起動時に自動で data/json/ へ変換（未変換ファイルのみ）
- 銘柄コードを入力 → Note 記事下書きプロンプトを生成

起動: streamlit run app.py
"""
from __future__ import annotations

import datetime
import json
import sys
import zipfile
from pathlib import Path

import streamlit as st

# XBRL → JSON 変換は著者環境のパーサー（C:\stock_analysis/collectors）に依存します。
# 無い環境では「変換」は動きませんが、事前変換済み JSON を data/json/ に置けばアプリは動きます。
_STOCK_ANALYSIS = Path(r"C:\stock_analysis")
if _STOCK_ANALYSIS.exists():
    sys.path.insert(0, str(_STOCK_ANALYSIS))

DATA_XBRL = Path(__file__).parent / "data" / "xbrl"
DATA_JSON  = Path(__file__).parent / "data" / "json"
DATA_XBRL.mkdir(parents=True, exist_ok=True)
DATA_JSON.mkdir(parents=True, exist_ok=True)

STATEMENTS_DIR = DATA_JSON  # find_json_files はこちらを参照
st.set_page_config(page_title="プロンプト作成 決算レビュー", page_icon="📝", layout="wide")

_NARROW_CSS = """<style>
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1100px !important;
    padding-left: 2rem !important; padding-right: 2rem !important;
    margin-left: auto !important; margin-right: auto !important;
}
</style>"""
st.session_state.setdefault("_wide_layout", False)
st.sidebar.checkbox("Wide 表示", key="_wide_layout")
if not st.session_state["_wide_layout"]:
    st.markdown(_NARROW_CSS, unsafe_allow_html=True)


# ── XBRL → JSON 自動変換 ───────────────────────────────────
def _detect_xbrl_type(path: Path) -> str:
    """'kessan' / 'yuho' / 'unknown' を返す。"""
    if path.suffix.lower() in (".htm", ".html"):
        return "kessan"
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
            if any("jpcrp030000-asr" in n for n in names):
                return "yuho"
            return "kessan"
        except Exception:
            return "unknown"
    return "unknown"


def _chg_pct(a, b) -> float | None:
    try:
        if a is not None and b and float(b) != 0:
            return round((float(a) - float(b)) / abs(float(b)) * 100, 1)
    except (TypeError, ValueError):
        pass
    return None


def _normalize_yuho(d: dict) -> dict:
    """有報 JSON に performance / balance_sheet / cash_flow キーを追加して返す。"""
    d["metadata"]["code"]          = d["metadata"].get("sec_code", "")
    d["metadata"]["document_name"] = "有価証券報告書"

    s5  = d.get("summary_5yr", {})
    cur = s5.get("current", {})
    pr1 = s5.get("prior1", {})

    # 有報サマリーが持つのは「経常利益」（営業利益ではない）。ordinary_income として渡す
    d["performance"] = {
        "current": {
            "net_sales":       cur.get("net_sales"),
            "ordinary_income": cur.get("ordinary_income"),
            "net_income":      cur.get("net_income"),
            "eps":             cur.get("eps"),
        },
        "prior_year": {
            "net_sales":       pr1.get("net_sales"),
            "ordinary_income": pr1.get("ordinary_income"),
            "net_income":      pr1.get("net_income"),
            "eps":             pr1.get("eps"),
        },
        "change_pct": {
            "net_sales":       _chg_pct(cur.get("net_sales"),       pr1.get("net_sales")),
            "ordinary_income": _chg_pct(cur.get("ordinary_income"), pr1.get("ordinary_income")),
            "net_income":      _chg_pct(cur.get("net_income"),      pr1.get("net_income")),
        },
    }
    d["balance_sheet"] = {"current": {
        "total_assets":           cur.get("total_assets"),
        "net_assets":             cur.get("net_assets"),
        "equity_to_assets_ratio": cur.get("equity_ratio"),
    }}
    d["cash_flow"] = {
        "operating": cur.get("operating_cf"),
        "investing":  cur.get("investing_cf"),
        "financing":  cur.get("financing_cf"),
    }
    return d


def _json_stem(src: Path, doc_type: str, d: dict) -> str:
    """保存する JSON のファイル名（拡張子なし）を生成。"""
    code = d.get("metadata", {}).get("code") or "unknown"
    fy   = d.get("metadata", {}).get("fiscal_year_end") or "unknown"
    suffix = "yuho" if doc_type == "yuho" else "FY"
    return f"{code}_{fy}_{suffix}"


def convert_pending() -> list[str]:
    """data/xbrl/ の未変換ファイルを data/json/ へ変換して変換済みファイル名を返す。"""
    done: list[str] = []
    for src in sorted(DATA_XBRL.glob("*")):
        if src.suffix.lower() not in (".htm", ".html", ".zip") or src.name.startswith("."):
            continue
        # 同名ステムの JSON が既存ならスキップ
        if list(DATA_JSON.glob(f"*{src.stem}*.json")):
            continue
        doc_type = _detect_xbrl_type(src)
        try:
            if doc_type == "kessan":
                from collectors.xbrl_to_json import convert as xbrl_convert
                xbrl_convert(src, out_dir=DATA_JSON)
            elif doc_type == "yuho":
                from collectors.parse_yuho_xbrl import parse_zip
                d = _normalize_yuho(parse_zip(src))
                stem = _json_stem(src, "yuho", d)
                out  = DATA_JSON / f"{stem}.json"
                out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                st.warning(f"{src.name}: XBRL 種別を判定できません")
                continue
            done.append(src.name)
        except ImportError:
            st.warning(
                f"{src.name}: XBRL→JSON パーサー（collectors）が見つかりません。"
                "変換は著者環境のパーサーに依存しています（公開準備中）。"
                "事前変換済みの JSON を `data/json/` に置いてご利用ください。"
            )
            break
        except Exception as e:
            st.warning(f"{src.name} の変換に失敗: {e}")
    return done


# ── データ取得 ──────────────────────────────────────────────
def find_json_files(code: str) -> list[Path]:
    """銘柄コードに一致するJSON（forecast / actual_secondary 除く）を新しい順で返す。"""
    results = []
    for f in STATEMENTS_DIR.glob(f"{code}_*.json"):
        if "forecast" in f.stem:
            continue
        try:
            m = json.load(open(f, encoding="utf-8")).get("metadata", {}) or {}
            if m.get("kind") == "actual_secondary":
                continue
        except Exception:
            pass
        results.append(f)
    return sorted(results, reverse=True)


@st.cache_data(show_spinner=False)
def read_meta(path: Path) -> dict:
    try:
        d = json.load(open(path, encoding="utf-8"))
        return d.get("metadata", {}) or {}
    except Exception:
        return {}


def _fix_name(s: str | None) -> str:
    """Shift-JIS バイトが Latin-1 として誤保存された社名を修復する。"""
    if not s:
        return ""
    try:
        return s.encode("latin-1").decode("cp932")
    except Exception:
        return s


def _v(x, unit: float = 1.0) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x) / unit:,.0f}"
    except (ValueError, TypeError):
        return str(x)


def _pct(x) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):+.1f}%"
    except (ValueError, TypeError):
        return str(x)


_SECTIONS = [
    {
        "label":  "経営成績の概況",
        "starts": ["当期の経営成績の概況", "経営成績等の概況", "経営成績の概況"],
        "ends":   ["当期の財政状態の概況", "財政状態の概況",
                   "キャッシュ・フローの概況", "次期の見通し", "会計基準の選択"],
        "chars":  3000,
    },
    {
        "label":  "次期の見通し（ガイダンス前提条件含む）",
        "starts": ["次期の見通し", "（４）次期の見通し", "4）次期の見通し"],
        "ends":   ["利益配分に関する", "会計基準の選択", "重要な後発事象", "以　上"],
        "chars":  1500,
    },
    {
        "label":  "重要な後発事象",
        "starts": ["重要な後発事象", "（重要な後発事象）"],
        "ends":   ["以　上", "以上"],
        "chars":  1500,
    },
]


def _find_source_zip(d: dict) -> Path | None:
    """JSON の _source.file から対応する ZIP を data/xbrl/ から探す。"""
    src_file = ((d.get("_source") or {}).get("file") or "").strip()
    if not src_file:
        return None
    for zp in DATA_XBRL.glob("*.zip"):
        try:
            with zipfile.ZipFile(zp) as zf:
                if any(src_file in n for n in zf.namelist()):
                    return zp
        except Exception:
            pass
    return None


def _extract_section(full: str, starts: list[str], ends: list[str],
                     max_chars: int) -> str:
    """full テキストから指定セクションを切り出す。目次重複を避けて2回目以降を採用。"""
    start = -1
    for marker in starts:
        idx = full.find(marker)
        if idx >= 0:
            second = full.find(marker, idx + 1)
            start = second if second >= 0 else idx
            break
    if start < 0:
        return ""
    excerpt = full[start:]
    end = len(excerpt)
    for end_marker in ends:
        idx = excerpt.find(end_marker, 80)
        if 0 < idx < end:
            end = idx
    excerpt = excerpt[:end].strip()
    return excerpt[:max_chars] + ("…" if len(excerpt) > max_chars else "")


def _extract_ixbrl_narrative(d: dict) -> str:
    """決算短信 ZIP の qualitative.htm から複数セクションのテキストを抽出する。"""
    if d.get("summary_5yr"):
        return ""
    zip_path = _find_source_zip(d)
    if not zip_path:
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            qual = next(
                (n for n in names if "qualitative" in n.lower() and n.lower().endswith(".htm")),
                None,
            )
            if not qual:
                return ""
            html_bytes = zf.read(qual)
    except Exception:
        return ""
    try:
        for enc in ("utf-8", "utf-8-sig", "cp932"):
            try:
                html_str = html_bytes.decode(enc); break
            except UnicodeDecodeError:
                continue
        else:
            html_str = html_bytes.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html_str, "html.parser")
        full = " ".join(soup.get_text(separator=" ", strip=True).split())
        blocks = []
        for sec in _SECTIONS:
            text = _extract_section(full, sec["starts"], sec["ends"], sec["chars"])
            if text:
                blocks.append(f"▶ {sec['label']}\n{text}")
        return "\n\n".join(blocks)
    except Exception:
        return ""


def _load_sibling_json(code: str, fy: str, kind: str) -> dict:
    """同じ銘柄の別期・別種別 JSON を STATEMENTS_DIR から読む。"""
    for p in STATEMENTS_DIR.glob(f"{code}_{fy}_*.json"):
        try:
            d2 = json.load(open(p, encoding="utf-8"))
            m2 = d2.get("metadata", {}) or {}
            if kind == "forecast" and "forecast" in p.stem:
                return d2
            if kind == "secondary" and m2.get("kind") == "actual_secondary":
                return d2
        except Exception:
            pass
    return {}


def _next_fy(fy_end: str) -> str:
    """'2026-03-31' → '2027-03-31' のように 1 年後の fiscal_year_end を返す。"""
    try:
        from datetime import date
        d = date.fromisoformat(fy_end)
        return date(d.year + 1, d.month, d.day).isoformat()
    except Exception:
        return ""


def _prev_fy(fy_end: str) -> str:
    """'2026-03-31' → '2025-03-31' のように 1 年前を返す。"""
    try:
        from datetime import date
        d = date.fromisoformat(fy_end)
        return date(d.year - 1, d.month, d.day).isoformat()
    except Exception:
        return ""


def extract_data_block(d: dict) -> str:
    meta  = d.get("metadata", {}) or {}
    perf  = d.get("performance", {}) or {}
    cur   = perf.get("current", {}) or {}
    pri   = perf.get("prior_year") or perf.get("prior") or {}
    chg   = perf.get("change_pct", {}) or {}
    fct   = perf.get("forecast", {}) or {}
    bs    = d.get("balance_sheet", {}) or {}
    bs_c  = bs.get("current", {}) or {}
    div   = d.get("dividend", {}) or {}
    div_c = div.get("actual_current", {}) or {}
    div_p = div.get("actual_prior", {}) or {}
    div_n = div.get("forecast_next", {}) or {}
    notes = d.get("notes", {}) or {}
    OKU   = 1e8
    code  = meta.get("code", "")
    fy    = meta.get("fiscal_year_end", "")

    # 前期データ: secondary ファイルから取得（逆算より正確）
    if not pri and code and fy:
        prev = _load_sibling_json(code, _prev_fy(fy), "secondary")
        if prev:
            pri = (prev.get("performance") or {}).get("current") or {}
    # secondary が無ければ change_pct から逆算
    if not pri and chg and cur:
        for k, v in cur.items():
            if k in chg and chg[k] is not None and v is not None:
                try:
                    pri[k] = float(v) / (1 + float(chg[k]) / 100)
                except (TypeError, ZeroDivisionError, ValueError):
                    pass

    # 来期ガイダンス: forecast ファイルから取得
    if not fct and code and fy:
        fc_d = _load_sibling_json(code, _next_fy(fy), "forecast")
        if fc_d:
            fct = (fc_d.get("performance") or {}).get("current") or {}
            # forecast ファイルの配当予想をマージ（キー名が異なるケースに対応）
            fc_div = fc_d.get("dividend") or {}
            fc_div_cur = (fc_div.get("forecast_current")
                          or fc_div.get("actual_current")
                          or fc_div.get("current") or {})
            if not div_n and fc_div_cur:
                div_n = fc_div_cur

    company = _fix_name(meta.get("company_name")) or "—"

    # 利益ラベル: 決算短信は「営業利益」、有報サマリーは「経常利益」を表示
    if cur.get("operating_income") is not None:
        inc_label, inc_key = "営業利益", "operating_income"
    elif cur.get("ordinary_income") is not None:
        inc_label, inc_key = "経常利益", "ordinary_income"
    else:
        inc_label, inc_key = "営業利益", "operating_income"

    lines = [
        "【基本情報】",
        f"銘柄       : {meta.get('code', '—')}　{company}",
        f"会計基準   : {meta.get('accounting_standard', '—')}　{'連結' if meta.get('consolidated') else '単独'}",
        f"決算期     : {meta.get('fiscal_year_end', '—')}　区分: {meta.get('period_type', '—')}",
        f"提出日     : {meta.get('filing_date', '—')}",
        "",
        "【業績（当期 / 前期 / 前期比）】",
        f"売上高     : {_v(cur.get('net_sales'), OKU)} 億円 / {_v(pri.get('net_sales'), OKU)} 億円 / {_pct(chg.get('net_sales'))}",
        f"{inc_label}   : {_v(cur.get(inc_key), OKU)} 億円 / {_v(pri.get(inc_key), OKU)} 億円 / {_pct(chg.get(inc_key))}",
        f"税前利益   : {_v(cur.get('profit_before_tax'), OKU)} 億円 / {_v(pri.get('profit_before_tax'), OKU)} 億円 / {_pct(chg.get('profit_before_tax'))}",
        f"純利益     : {_v(cur.get('net_income'), OKU)} 億円 / {_v(pri.get('net_income'), OKU)} 億円 / {_pct(chg.get('net_income'))}",
        f"EPS        : {_v(cur.get('eps'))} 円 / {_v(pri.get('eps'))} 円",
    ]

    if any(fct.get(k) for k in ("net_sales", "operating_income", "net_income")):
        # 当期実績からの変化率を計算（Claudeに推算させず正確な値を渡す）
        def _fct_chg(fct_val, cur_val) -> str:
            try:
                if fct_val and cur_val and float(cur_val) != 0:
                    return _pct(round((float(fct_val) / float(cur_val) - 1) * 100, 1))
            except (TypeError, ValueError, ZeroDivisionError):
                pass
            return "—"

        lines += [
            "",
            "【来期ガイダンス（当期実績比）】",
            f"売上高（予）  : {_v(fct.get('net_sales'), OKU)} 億円 / {_fct_chg(fct.get('net_sales'), cur.get('net_sales'))}",
            f"営業利益（予）: {_v(fct.get('operating_income'), OKU)} 億円 / {_fct_chg(fct.get('operating_income'), cur.get('operating_income'))}",
            f"純利益（予）  : {_v(fct.get('net_income'), OKU)} 億円 / {_fct_chg(fct.get('net_income'), cur.get('net_income'))}",
            f"EPS（予）     : {_v(fct.get('eps'))} 円",
        ]

    lines += [
        "",
        "【バランスシート（当期末）】",
        f"総資産       : {_v(bs_c.get('total_assets'), OKU)} 億円",
        f"純資産       : {_v(bs_c.get('net_assets'), OKU)} 億円",
        f"自己資本比率 : {_v(bs_c.get('equity_to_assets_ratio'))} %",
        "",
        "【配当（年間・1株あたり）】",
        f"当期実績 : {_v(div_c.get('annual'))} 円　（前期: {_v(div_p.get('annual'))} 円）",
        f"次期予想 : {_v(div_n.get('annual'))} 円",
    ]

    segs = d.get("segments") or []
    if segs and isinstance(segs, list):
        lines += ["", "【セグメント（売上高 / 営業利益）】"]
        for s in segs:
            if not isinstance(s, dict):
                continue
            name = s.get("segment_name") or s.get("name") or "—"
            rev  = _v(s.get("net_sales") or s.get("revenue"), OKU)
            oi   = _v(s.get("operating_income"), OKU)
            lines.append(f"  {name}: {rev} 億円 / {oi} 億円")

    cf = d.get("cash_flow", {}) or {}
    cf_op  = cf.get("operating") or cf.get("operating_activities")
    cf_inv = cf.get("investing") or cf.get("investing_activities")
    cf_fin = cf.get("financing") or cf.get("financing_activities")
    if any(x is not None for x in (cf_op, cf_inv, cf_fin)):
        lines += [
            "",
            "【キャッシュフロー】",
            f"営業CF : {_v(cf_op, OKU)} 億円",
            f"投資CF : {_v(cf_inv, OKU)} 億円",
            f"財務CF : {_v(cf_fin, OKU)} 億円",
        ]

    # 有報のみ: 5年業績推移
    s5 = d.get("summary_5yr") or {}
    if s5:
        yr_order = ["prior4", "prior3", "prior2", "prior1", "current"]
        has = [k for k in yr_order if k in s5]
        if has:
            lines += ["", "【5年業績推移（売上高 / 経常利益 / 純利益）億円】"]
            for k in has:
                p   = s5[k]
                ns  = _v(p.get("net_sales"),       OKU)
                oi  = _v(p.get("ordinary_income"),  OKU)
                ni  = _v(p.get("net_income"),       OKU)
                roe = _v(p.get("roe"))
                lines.append(f"  {k}: 売上 {ns} / 経常 {oi} / 純利 {ni} / ROE {roe}%")

    op = notes.get("operating_results") or ""
    if op and len(op) > 10:
        lines += ["", "【経営概況（短信ノート）】", op[:1200] + ("…" if len(op) > 1200 else "")]

    # iXBRL テキストブロックを追加（決算短信のみ）
    narrative = _extract_ixbrl_narrative(d)
    if narrative:
        lines += ["", "【事業概況・セグメント解説（iXBRL テキスト）】", narrative]

    return "\n".join(lines)


PROMPT_TEMPLATE = """\
提供された決算データをもとに、**個人投資家向けのNote記事の下書き**を作成してください。

## 対象読者
株式投資に関心のある個人投資家（中級者）。財務諸表の基礎知識はあるが、この企業固有の文脈は詳しくない。

## ステップ0：テーゼを先に決める（本文を書く前に必ず実行）
この決算で「最も重要な1つのメッセージ」を1文で定義してください。
テーゼは「数字の羅列」でなく「だから何か」を含む命題（例：「増収だが構造的な利益率低下が始まっている」）。

## 記事構成（合計 1,800〜2,500字）

1. **リード文**（150〜200字）
   - テーゼを冒頭で言い切る。数字を1つ入れる
   - 読者が「続きを読みたい」と感じるフック

2. **業績ハイライト**（500〜600字）
   - 売上・営業利益・純利益の前期比を示す
   - 各指標について「なぜその数字になったか」の背景を必ず1文添える
   - 「数字の羅列」にならないよう、因果関係で繋ぐ

3. **構造分析**（500〜600字）
   - 一時要因（在庫評価・為替・減損・のれん）と実力ベースを分離する
   - セグメント間の格差・成長エンジンの変化を読む
   - 「今期だけ見ていると見誤るポイント」を明示する

4. **来期見通し**（300〜350字）
   - ガイダンス数値と今期実績の連続性・断絶を評価する
   - 投資家が次の決算までに注目すべき指標・イベントを2〜3つ挙げる

5. **まとめ**（200〜250字）
   - テーゼに戻って3行で総括
   - 「この決算後に変わったこと・変わらなかったこと」を対比する

## 制約
- 断定的な売買推奨はしない（「〜の可能性があります」「〜が注目されます」）
- 数字は具体的に（「大幅増益」より「営業利益 +XX%」）
- 事実とコメントは【事実】【解釈】と明示して区別する
- 敬体（です・ます調）

## データの限界（必ず守ること）
以下の情報は XBRL・決算短信本体に含まれないため、提供データには存在しません。
データにない情報を「未開示」「不明」と記述したり、推測で補ったりしないこと。
- 中期経営計画・事業戦略の詳細（別資料）
- 決算説明会・IR プレゼン資料の追加コメント
- 決算短信本体に記載のない補足資料の数値

※ 決算短信本体（後発事象・次期見通し含む）は提供データに含まれます。
これらに言及が必要な場合は「追加メモ」に記載された情報のみ使用すること。

## 決算データ（{doc_type}）
{data}

## 追加メモ・着目点
{memo}\
"""


# ── 起動時 XBRL 自動変換 ────────────────────────────────────
_auto = convert_pending()
if _auto:
    st.toast(f"XBRL を変換しました: {', '.join(_auto)}")


# ── サイドバー ──────────────────────────────────────────────

st.sidebar.markdown("# 決算レビュー作成アプリ", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("### ⬛ プロンプト作成", unsafe_allow_html=True)

# ─ プロンプト生成 ───────────────────────────────────────────

code_prompt = st.sidebar.text_area("銘柄コード", height=68, placeholder="例: 5020")
memo        = st.sidebar.text_area("着目点・追加メモ", height=68,
                                   placeholder="例: 在庫評価益の一時的要因を除いた実力値を強調してほしい")

# XBRLファイル選択（常時表示）
def _file_label(p: Path) -> str:
    m   = read_meta(p)
    doc = m.get("document_name") or ""
    kind = "決算短信" if "決算短信" in doc else ("有報" if "有価証券報告書" in doc else "")
    return f"{p.stem}　{kind}" if kind else p.stem

_code = code_prompt.strip()
if _code:
    _files = find_json_files(_code)
else:
    # コード未入力時は全 JSON を表示
    _files = sorted(
        [f for f in STATEMENTS_DIR.glob("*.json")
         if "forecast" not in f.stem
         and (read_meta(f).get("kind") or "") != "actual_secondary"],
        reverse=True,
    ) if STATEMENTS_DIR.exists() else []

sel_file: Path | None = None
doc_type: str = ""

if _files:
    _labels   = {_file_label(f): f for f in _files}
    _sel_label = st.sidebar.selectbox("XBRLファイル選択", list(_labels))
    sel_file   = _labels[_sel_label]
    doc_type   = read_meta(sel_file).get("document_name") or sel_file.stem
    st.sidebar.caption(f"📄 {doc_type}")
else:
    st.sidebar.selectbox("XBRLファイル選択", ["（JSONファイルなし）"], disabled=True)

btn_prompt = st.sidebar.button("プロンプトを作成", disabled=sel_file is None,
                                use_container_width=True)

# ─ XBRL取得・変換（expander） ──────────────────────────────
st.sidebar.divider()

st.sidebar.markdown("### ⬛ XBRL 取得", unsafe_allow_html=True)

with st.sidebar.expander("データ取得"):
    code_xbrl   = st.text_input("銘柄コード（XBRL取得用）", placeholder="例: 5020")
    has_xbrl    = bool(code_xbrl.strip())
    kessan_date = st.date_input("決算短信発表日", value=datetime.date.today())
    btn_kessan  = st.button("決算短信 XBRL 取得", disabled=not has_xbrl,
                             use_container_width=True)
    yuho_year   = st.number_input("有報提出年", min_value=2010, max_value=2035,
                                   value=datetime.date.today().year, step=1)
    btn_yuho    = st.button("有報 XBRL 取得", disabled=not has_xbrl,
                             use_container_width=True)
    btn_convert = st.button("JSON 変換", use_container_width=True)

st.sidebar.divider()

# ── メイン ──────────────────────────────────────────────────
_APP_DIR = str(Path(__file__).parent)

if btn_kessan and has_xbrl:
    if _APP_DIR not in sys.path:
        sys.path.insert(0, _APP_DIR)
    try:
        from fetch_kessan import run as _run_kessan
        with st.spinner("決算短信 XBRL 取得中..."):
            n = _run_kessan(code_xbrl.strip(), [kessan_date])
        if n:
            st.success(f"{n} 件取得 → `data/xbrl/`　「JSON 変換」ボタンで変換してください")
        else:
            st.warning("0 件取得。指定日に決算短信の開示がないか、iXBRL の URL パターンが一致しませんでした。TDnet から手動でダウンロードして `data/xbrl/` に置いてください。")
    except Exception as e:
        st.error(f"取得に失敗しました: {e}")

elif btn_yuho and has_xbrl:
    if _APP_DIR not in sys.path:
        sys.path.insert(0, _APP_DIR)
    try:
        from fetch_yuho import run as _run_yuho
        with st.spinner("有報 XBRL 取得中（数分かかる場合があります）..."):
            n = _run_yuho(code=code_xbrl.strip(), edinet_code=None, year=int(yuho_year))
        if n:
            st.success(f"{n} 件取得 → `data/xbrl/`　「JSON 変換」ボタンで変換してください")
        else:
            st.warning("0 件取得。指定年に有報の提出がないか、まだ未提出の可能性があります。")
    except Exception as e:
        st.error(f"取得に失敗しました: {e}")

elif btn_convert:
    with st.spinner("JSON 変換中..."):
        done = convert_pending()
    if done:
        st.success(f"変換完了: {', '.join(done)}")
        st.rerun()
    else:
        st.info("変換対象ファイルがありません（既に変換済みか `data/xbrl/` が空です）")

elif btn_prompt and sel_file:
    try:
        d = json.load(open(sel_file, encoding="utf-8"))
    except Exception as e:
        st.error(f"JSON 読み込みエラー: {e}")
        st.stop()

    data_block = extract_data_block(d)
    prompt     = PROMPT_TEMPLATE.format(
        doc_type=doc_type or sel_file.stem,
        data=data_block,
        memo=memo.strip() or "（特になし）",
    )
    st.subheader("生成プロンプト")
    st.caption("右上のアイコンでコピーできます。")
    st.code(prompt, language="markdown")
    with st.expander("抽出データを確認"):
        st.text(data_block)

else:
    st.info("👈 XBRLファイルを選択し、「プロンプトを作成」を押してください")
