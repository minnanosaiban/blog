"""
連載 2-8 企業価値分析（EV・DCF） サムネイル生成
出力: docs/blog/posts/img/18_enterprise_value/00_thumbnail.png
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

BG = '#0d1b2a'
BLUE_L = '#5fa8e5'
RED_L = '#e58a8a'
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
ax_l.text(0.110, 0.902, '連載 2-8', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'EV / DCF', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '株価に借金を足すと', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '会社の値段が見える', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# ── 右: EV 構成の概念図（時価総額 + ネットデット = EV、DCF と突き合わせ）──
ax_r = fig.add_axes([0.47, 0.10, 0.48, 0.78], facecolor=BG)
ax_r.set_xlim(0, 10)
ax_r.set_ylim(0, 10)
ax_r.axis('off')

ax_r.text(0.2, 9.3, '会社まるごとの値段（EV）', color=WHITE, fontsize=24, ha='left', va='center', fontweight='bold')

BAR_H = 1.5
rows = [
    (6.4, 4.6, 1.8),   # y, 時価総額, ネットデット
    (3.9, 3.2, 1.1),
    (1.4, 2.2, 0.5),
]
for y, mc, nd in rows:
    ax_r.add_patch(patches.FancyBboxPatch((0.2, y), mc, BAR_H,
                   boxstyle='round,pad=0,rounding_size=0.08', facecolor=BLUE_L, linewidth=0))
    ax_r.add_patch(patches.FancyBboxPatch((0.2 + mc, y), nd, BAR_H,
                   boxstyle='round,pad=0,rounding_size=0.08', facecolor=RED_L, linewidth=0))

ax_r.text(0.2 + 4.6 / 2, 6.4 + BAR_H / 2, '時価総額', color=BG, fontsize=24,
          ha='center', va='center', fontweight='bold')
ax_r.text(0.2 + 4.6 + 0.9, 6.4 + BAR_H / 2, '借金', color=BG, fontsize=24,
          ha='center', va='center', fontweight='bold')

# DCF の突き合わせライン
ax_r.plot([7.6, 7.6], [0.7, 8.6], color=GREEN, lw=3, ls='--')
ax_r.text(7.85, 8.2, 'DCF', color=GREEN, fontsize=28, ha='left', va='center', fontweight='bold')
ax_r.text(7.85, 7.3, 'FCFの', color=SOFT, fontsize=18, ha='left', va='center')
ax_r.text(7.85, 6.6, '永続価値', color=SOFT, fontsize=18, ha='left', va='center')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/18_enterprise_value/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
