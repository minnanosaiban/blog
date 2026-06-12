"""
連載12 セグメント発進力 サムネイル生成
出力: docs/blog/posts/img/08_segment_analysis/00_thumbnail.png
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
MUTED_BG = '#1a2535'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 2-5', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'セグメント', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '事業別成長で', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '次の主力事業を発掘', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

# 横棒グラフ（輪郭スタイル）
zero_x = 40
scale  = 0.28

segments = [
    (80, 'テストシステム', +50.9, GREEN),
    (53, '次世代事業',    +127,  BLUE_L),
    (26, '金融',         -55,   '#ff6b6b'),
]

for y, name, growth, color in segments:
    w = growth * scale
    x0 = zero_x if growth > 0 else zero_x + w
    ax_r.add_patch(patches.Rectangle((x0, y-8), abs(w), 16,
                                     facecolor=color, edgecolor='none', alpha=0.18))
    ax_r.add_patch(patches.Rectangle((x0, y-8), abs(w), 16,
                                     facecolor='none', edgecolor=color, alpha=0.75, linewidth=2))
    ax_r.text(zero_x-2, y, name, color=WHITE, fontsize=24,
              ha='right', va='center', fontweight='bold')
    end_x = zero_x + w
    sign = '+' if growth > 0 else ''
    offset = 3 if growth > 0 else -3
    ha = 'left' if growth > 0 else 'right'
    ax_r.text(end_x + offset, y, f'{sign}{growth:.0f}%', color=color, fontsize=24,
              ha=ha, va='center', fontweight='bold')

ax_r.plot([zero_x, zero_x], [10, 96], color=SOFT, linewidth=1.5, alpha=0.5)

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/08_segment_analysis/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
