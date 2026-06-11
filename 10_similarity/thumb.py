"""
連載15 類似決算検索 サムネイル生成
出力: docs/blog/posts/img/10_similar_earnings_search/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 3-1', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'コサイン', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.text(0.80, 0.69, '類似度', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '数値特徴量で', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '「類似決算」を発見', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(-3.5, 3.5)
ax_r.set_ylim(-3.5, 3.5)
ax_r.axis('off')

import numpy as np
np.random.seed(42)

# 類似企業クラスタ（商社）
cluster = [[0.5, 0.3], [0.75, 0.1], [0.35, 0.55], [0.9, 0.45], [0.2, 0.2]]
for pos in cluster:
    ax_r.plot(pos[0], pos[1], 'o', color=GREEN, markersize=11, alpha=0.55)

# 類似範囲の円
circle = patches.Circle((0.54, 0.32), 0.75, fill=False,
                         edgecolor=GREEN, linewidth=2, linestyle='--', alpha=0.6)
ax_r.add_patch(circle)
ax_r.text(0.54, 1.45, '類似企業群', color=GREEN, fontsize=28,
          ha='center', va='bottom')

# 丸紅（クエリ）
ax_r.plot(0.5, 0.3, 'o', color=WHITE, markersize=18,
          markeredgecolor=GREEN, markeredgewidth=3, zorder=5)
ax_r.text(1.55, 0.3, '丸紅', color=WHITE, fontsize=28,
          ha='left', va='center', fontweight='bold')

# 外れ点（実績）
ax_r.plot(-2.2, -2.0, 'o', color='#ff6b6b', markersize=14, alpha=0.85, zorder=5)
ax_r.text(-2.2, -1.5, '丸紅実績', color='#ff6b6b', fontsize=28,
          ha='center', va='bottom', fontweight='bold')

# 結果ボックス（類似平均 vs 自身実績 ― 1 枚の箱に 2 行）
ax_r.add_patch(patches.FancyBboxPatch((-3.3, -3.35), 6.6, 1.55,
                                      boxstyle='round,pad=0.1',
                                      facecolor=MUTED_BG, edgecolor=SOFT, linewidth=1.5))
# 1行目: 類似平均
ax_r.text(-0.3, -2.45, '類似平均', color=GREEN, fontsize=28,
          ha='right', va='center', fontweight='bold')
ax_r.text(0.3, -2.45, '+2.39%', color=GREEN, fontsize=28,
          ha='left', va='center', fontweight='bold')
# 2行目: 自身実績
ax_r.text(-0.3, -3.00, '自身実績', color='#ff6b6b', fontsize=28,
          ha='right', va='center', fontweight='bold')
ax_r.text(0.3, -3.00, '−9.39%', color='#ff6b6b', fontsize=28,
          ha='left', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/10_similar_earnings_search/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
