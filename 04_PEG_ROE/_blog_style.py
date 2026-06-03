"""blog 画像生成の共通スタイル設定と保存ヘルパー（全 NN_*_make_images.py 共有）。

■ 目的
  全チャートの「横幅」を 1 つに固定することで、mkdocs 掲載時の縮小率を一定にし、
  グラフ内の文字サイズが記事間でバラつかないようにする。

  画面上の文字サイズ ＝ 画像内の文字px × (本文カラム幅 / PNGの横px)
  文字px（= font.size × dpi）は全画像で同一なので、PNG の横 px を揃えれば
  縮小率が一定になり、文字サイズも揃う。

■ 使い方（各 NN_*_make_images.py の冒頭）
      import _blog_style as bs
      bs.apply_rcparams()
      FIG_W = bs.FIG_W                 # すべての figure の幅はこれで固定する
      _savefig_vpad = bs.savefig_uniform   # 既存の呼び出し名のまま使う場合

      fig, ax = plt.subplots(figsize=(FIG_W, 6))   # 幅は必ず FIG_W、高さは自由
      ...
      bs.savefig_uniform(fig, OUT_DIR / "01_xxx.png")

■ ルール
  - figure の幅は必ず FIG_W インチにする（高さは自由に変えてよい）。
    内容が多くて横に入り切らない場合は「行を増やす／列を減らす」で対応し、
    figure を横に広げない（広げると文字が相対的に小さくなる）。
  - savefig_uniform が tight 切り抜き後に左右へ白を均等に足し、出力 PNG の
    横 px を常に round(FIG_W * DPI) に揃える。tight 切り抜きの揺れを吸収する。
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# ── 全チャート共通の基準値 ──────────────────────────────────────────────
FIG_W = 13.0                       # すべての figure の幅（インチ）。
DPI = 144                          # 出力解像度。
TARGET_W_PX = round(FIG_W * DPI)   # 全 PNG をこの横 px に統一（= 1872）。

FONT_STACK = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP"]


def apply_rcparams() -> None:
    """全スクリプト共通の matplotlib 設定。各スクリプト冒頭で 1 回呼ぶ。"""
    mpl.rcParams["font.family"] = FONT_STACK
    mpl.rcParams["axes.unicode_minus"] = False
    mpl.rcParams["figure.facecolor"] = "white"
    mpl.rcParams["axes.facecolor"] = "white"
    mpl.rcParams["savefig.facecolor"] = "white"
    mpl.rcParams["savefig.bbox"] = "tight"
    mpl.rcParams["savefig.dpi"] = DPI
    mpl.rcParams["savefig.pad_inches"] = 0       # 左右・上の余白は savefig_uniform で制御
    mpl.rcParams["axes.titlepad"] = 40
    mpl.rcParams["font.size"] = 16
    mpl.rcParams["axes.titlesize"] = 20
    mpl.rcParams["axes.labelsize"] = 16
    mpl.rcParams["xtick.labelsize"] = 16
    mpl.rcParams["ytick.labelsize"] = 16
    mpl.rcParams["legend.fontsize"] = 16


def savefig_uniform(fig, path, tpad: float = 0.4, bpad: float = 0.5,
                    target_w_px: int = TARGET_W_PX) -> None:
    """横 px を target_w_px に統一して PNG 保存する。

    1. tight + pad_inches=0 で余白を切り詰めて一旦レンダリング。
    2. 左右へ白を均等に足して横 px を target_w_px ちょうどに揃える。
       （figure の幅を FIG_W にしてあれば tight 後の横幅は必ず target 以下）
    3. 上 tpad / 下 bpad インチの白余白を足す。

    figure の幅を FIG_W に揃えてあれば全画像の横 px が一致し、mkdocs での
    縮小率＝グラフ内の文字サイズが記事間で揃う。
    """
    dpi = fig.dpi
    buf = io.BytesIO()
    fig.savefig(buf, bbox_inches="tight", pad_inches=0, format="png")
    buf.seek(0)
    img = plt.imread(buf)                         # RGBA float32 (H, W, 4)

    # ── 横幅を target_w_px に正規化 ──
    h, w, ch = img.shape[0], img.shape[1], img.shape[2]
    if w > target_w_px:
        # tight 切り抜き後の横幅が target を超えるケース（軸外のラベル等が figure 幅を
        # はみ出している）。アスペクト比を保ったまま target_w_px に縮小する。
        # （この図だけ文字が僅かに小さくなるので、警告を出して把握できるようにする）
        scale = target_w_px / w
        new_h = max(1, round(h * scale))
        try:
            from PIL import Image
            im = Image.fromarray((np.clip(img, 0.0, 1.0) * 255).astype(np.uint8))
            im = im.resize((target_w_px, new_h), Image.LANCZOS)
            img = np.asarray(im).astype(np.float64) / 255.0
        except Exception:
            # PIL 不在時: 最近傍で縦横とも縮小（縦横比は保つ）
            ci = np.linspace(0, w - 1, target_w_px).round().astype(int)
            ri = np.linspace(0, h - 1, new_h).round().astype(int)
            img = img[np.ix_(ri, ci)]
        print("  [warn] %s: tight width %dpx > target %dpx -> %.0f%% に縮小"
              % (Path(path).name, w, target_w_px, scale * 100))
        h, w, ch = img.shape[0], img.shape[1], img.shape[2]
    if w < target_w_px:
        pad = target_w_px - w
        left = pad // 2
        right = pad - left
        white_l = np.ones((h, left, ch), dtype=img.dtype)
        white_r = np.ones((h, right, ch), dtype=img.dtype)
        img = np.hstack([white_l, img, white_r])

    # ── 上下の白余白 ──
    parts = []
    top_rows = max(0, round(tpad * dpi))
    bot_rows = max(0, round(bpad * dpi))
    if top_rows:
        parts.append(np.ones((top_rows, img.shape[1], ch), dtype=img.dtype))
    parts.append(img)
    if bot_rows:
        parts.append(np.ones((bot_rows, img.shape[1], ch), dtype=img.dtype))
    out = np.vstack(parts) if len(parts) > 1 else img

    plt.imsave(str(path), out, dpi=dpi)
