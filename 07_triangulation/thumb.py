"""
連載11 予想検証 サムネイル生成
出力: docs/blog/posts/img/07_triangulation/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 2-4', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, '予想 × 業績', color=WHITE, fontsize=60, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '予想のズレを', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '見抜く', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

import math
cx, cy, radius = 46, 50, 30

p1 = (cx, cy + radius)                                                        # 業績（頂点）
p2 = (cx - radius * math.cos(math.pi/6), cy - radius * math.sin(math.pi/6))   # ガイダンス（左下）
p3 = (cx + radius * math.cos(math.pi/6), cy - radius * math.sin(math.pi/6))   # コンセンサス（右下）

# 三角形（塗り＋枠線）
triangle = patches.Polygon([p1, p2, p3], facecolor=BLUE_L, edgecolor='none', alpha=0.10)
ax_r.add_patch(triangle)
for (a_, b_), color in [((p1, p2), BLUE_L), ((p2, p3), SOFT), ((p3, p1), GREEN)]:
    ax_r.plot([a_[0], b_[0]], [a_[1], b_[1]], color=color, linewidth=2.5, alpha=0.8)

# 頂点ラベル（三角形の外側・大きめ・重なりなし）
ax_r.text(p1[0], p1[1] + 6, '業績', color=GREEN, fontsize=26,
          ha='center', va='bottom', fontweight='bold')
ax_r.text(p2[0], p2[1] - 7, 'ガイダンス', color=BLUE_L, fontsize=26,
          ha='center', va='top', fontweight='bold')
ax_r.text(p3[0], p3[1] - 7, 'コンセンサス', color='#22d4a8', fontsize=26,
          ha='center', va='top', fontweight='bold')

# 中央
ax_r.scatter([cx], [cy], s=200, color=WHITE, zorder=5, edgecolors=BLUE_L, linewidths=2)
ax_r.text(cx, cy - 9, '検証点', color=WHITE, fontsize=24, ha='center', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/07_triangulation/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
