"""
連載 3-4 ランダムフォレスト サムネイル生成
出力: docs/blog/posts/img/13_random_forest/00_thumbnail.png
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

BG = '#0d1b2a'
BLUE_L = '#5fa8e5'
GREEN = '#22c55e'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 3-4', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'ランダムフォレスト', color=WHITE, fontsize=56, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '予測は失敗！決算から ', color=BLUE_L, fontsize=32, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, 'CAR は当てられない', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')


def tree(cx, base, h, w, col):
    ax_r.add_patch(patches.Polygon([(cx - w, base), (cx + w, base), (cx, base + h)],
                                   facecolor=col, edgecolor=BG, linewidth=1.5, alpha=0.88))
    ax_r.add_patch(patches.Rectangle((cx - 2.2, base - 10), 4.4, 10, facecolor=SOFT, edgecolor='none'))


# ランダム「フォレスト」＝木を3本
for cx, col in [(26, GREEN), (50, BLUE_L), (74, '#22d4a8')]:
    tree(cx, 44, 34, 15, col)

ax_r.text(50, 17, '数値だけでは当たらない', color=WHITE, fontsize=26,
          ha='center', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/13_random_forest/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
