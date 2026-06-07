"""
連載 3-3 決算クラスタリング サムネイル生成
出力: docs/blog/posts/img/12_earnings_clustering/00_thumbnail.png
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

BG = '#0d1b2a'
BLUE_L = '#5fa8e5'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 3-3', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'K-means', color=WHITE, fontsize=60, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '教師なし学習が分けた', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '「決算の型」', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

# 3 つのクラスタ（型A/型B/型C の色に対応した点群）
rng = np.random.default_rng(7)
blobs = [((70, 62), '#E26A2C', 14, 9), ((35, 73), '#A23B72', 12, 8), ((47, 33), '#6FA8D6', 24, 11)]
for (cx, cy), col, n, sp in blobs:
    xs = rng.normal(cx, sp, n)
    ys = rng.normal(cy, sp, n)
    ax_r.scatter(xs, ys, s=130, color=col, alpha=0.78, edgecolors=BG, linewidths=0.8)

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/12_earnings_clustering/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
