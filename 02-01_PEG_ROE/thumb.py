"""
連載01 Note サムネイル生成
出力: docs/blog/posts/img/04_garp_peg_roe/00_thumbnail.png
サイズ: 1280x670 px（Note 推奨 16:9）
実行: python docs/blog/scripts/thumb_01_garp.py

設計方針:
  - 全要素を「サムネイル縮小表示でも読める最小サイズ」に統一
  - 巨大な単一要素を作らず、適度なサイズ感でバランス重視
  - 概念図の文字はサブラベルも含め全て判読可能に
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

# ---- カラー ----
BG       = '#0d1b2a'
PANEL    = '#162236'
BLUE_L   = '#5fa8e5'
GREEN    = '#22c55e'
GREEN_BG = '#0e3a23'
MUTED_BG = '#1a2535'
MUTED_TX = '#a5b8cc'
WHITE    = '#f5f8fc'
SOFT     = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ===== 左エリア（タイトル）画面幅の 44% =====
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

# 連載番号バー
ax_l.add_patch(patches.Rectangle(
    (0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0
))
ax_l.text(0.110, 0.902, '連載 2-1', color=BLUE_L,
          fontsize=24, va='center', ha='left', fontweight='bold')

# タイトル: GARP
ax_l.text(0.07, 0.69, 'GARP', color=WHITE,
          fontsize=72, va='center', ha='left', fontweight='bold')

# 区切り線
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))

# キャッチコピー
ax_l.text(0.07, 0.48, '成長と割安を', color=BLUE_L,
          fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '両立する銘柄を発掘', color=WHITE,
          fontsize=36, va='center', ha='left', fontweight='bold')

# 英語フルネーム

# ===== 右エリア（象限図）画面幅の 52% =====
ax_r = fig.add_axes([0.46, 0.10, 0.50, 0.80], facecolor=BG)
ax_r.set_xlim(-0.25, 2.05)
ax_r.set_ylim(-0.32, 2.25)
ax_r.axis('off')

# 4象限の背景
zones = [
    (0, 1, 1, 1, GREEN_BG),
    (1, 1, 1, 1, MUTED_BG),
    (0, 0, 1, 1, MUTED_BG),
    (1, 0, 1, 1, MUTED_BG),
]
for (x, y, w, h, fc) in zones:
    ax_r.add_patch(patches.Rectangle(
        (x, y), w, h, facecolor=fc, edgecolor='none'
    ))

# GARP ゾーンの強調枠
ax_r.add_patch(patches.Rectangle(
    (0, 1), 1, 1, fill=False, edgecolor=GREEN, linewidth=3
))

# 中央十字（薄く）
ax_r.plot([1, 1], [0, 2], color=SOFT, linewidth=0.8, alpha=0.3)
ax_r.plot([0, 2], [1, 1], color=SOFT, linewidth=0.8, alpha=0.3)

# ---- GARP ゾーンのラベル ----
ax_r.text(0.50, 1.72, '★', color=GREEN,
          fontsize=32, ha='center', va='center', fontweight='bold')
ax_r.text(0.50, 1.48, 'GARP', color=GREEN,
          fontsize=32, ha='center', va='center', fontweight='bold')
ax_r.text(0.50, 1.24, '理想ゾーン', color=WHITE,
          fontsize=24, ha='center', va='center', fontweight='bold')

# ---- 他象限ラベル ----
other_zones = [
    (1.50, 1.55, '過熱グロース',    MUTED_TX, 24),
    (0.50, 0.55, 'バリュートラップ', MUTED_TX, 24),
    (1.50, 0.55, '投資不適格',      MUTED_TX, 24),
]
for (x, y, txt, color, fs) in other_zones:
    ax_r.text(x, y, txt, color=color, fontsize=fs,
              ha='center', va='center')

# ---- 軸ラベル ----
# X軸（PEG）
ax_r.annotate('', xy=(2.05, -0.14), xytext=(-0.05, -0.14),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=1.4, alpha=0.7))
ax_r.text(0.50, -0.14, '割安', color=SOFT, fontsize=24,
          ha='center', va='center', fontweight='bold',
          bbox=dict(boxstyle='round,pad=0.3', facecolor=BG, edgecolor='none'))
ax_r.text(1.50, -0.14, '割高', color=SOFT, fontsize=24,
          ha='center', va='center', fontweight='bold',
          bbox=dict(boxstyle='round,pad=0.3', facecolor=BG, edgecolor='none'))
ax_r.text(1.00, -0.36, 'PEG', color=SOFT, fontsize=24,
          ha='center', va='center', alpha=0.9, fontweight='bold')

# Y軸（ROE）
ax_r.annotate('', xy=(-0.15, 2.05), xytext=(-0.15, -0.05),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=1.4, alpha=0.7))
ax_r.text(-0.15, 0.50, '低', color=SOFT, fontsize=24,
          ha='center', va='center', fontweight='bold',
          bbox=dict(boxstyle='round,pad=0.25', facecolor=BG, edgecolor='none'))
ax_r.text(-0.15, 1.50, '高', color=SOFT, fontsize=24,
          ha='center', va='center', fontweight='bold',
          bbox=dict(boxstyle='round,pad=0.25', facecolor=BG, edgecolor='none'))
ax_r.text(-0.15, 2.24, 'ROE', color=SOFT, fontsize=24,
          ha='center', va='center', alpha=0.9, fontweight='bold')

# 出力
OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/04_garp_peg_roe/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
