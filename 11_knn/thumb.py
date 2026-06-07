"""
連載16 K-NN予測 サムネイル生成
出力: docs/blog/posts/img/11_knn_prediction/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 3-2', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'K-NN回帰', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '失敗が生んだ', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '個別ショック検出器', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.08, 0.50, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

# 左カード: 予測失敗
ax_r.add_patch(patches.FancyBboxPatch((3, 28), 43, 60,
                                      boxstyle='round,pad=1.5',
                                      facecolor=MUTED_BG, edgecolor='#ff6b6b', linewidth=2))
ax_r.text(24.5, 80, '予測', color='#ff6b6b', fontsize=24,
          ha='center', va='center', fontweight='bold')
ax_r.text(24.5, 67, 'r = −0.03', color='#ff6b6b', fontsize=24,
          ha='center', va='center', fontweight='bold')
ax_r.text(24.5, 47, 'ベースライン以下', color=SOFT, fontsize=24, ha='center', va='center')
ax_r.text(24.5, 32, '×  失敗', color='#ff6b6b', fontsize=24,
          ha='center', va='center', fontweight='bold')

# 右カード: 発見器として活用
ax_r.add_patch(patches.FancyBboxPatch((54, 28), 43, 60,
                                      boxstyle='round,pad=1.5',
                                      facecolor=MUTED_BG, edgecolor=GREEN, linewidth=2))
ax_r.text(75.5, 80, '乖離', color=GREEN, fontsize=24,
          ha='center', va='center', fontweight='bold')
ax_r.text(75.5, 67, '= ショック', color=GREEN, fontsize=24,
          ha='center', va='center', fontweight='bold')
ax_r.text(75.5, 47, 'ショック検出器', color=WHITE, fontsize=24, ha='center', va='center')
ax_r.text(75.5, 32, '✓  実用化', color=GREEN, fontsize=24,
          ha='center', va='center', fontweight='bold')

# フッター
ax_r.text(50, 15, 'AIは「予測」でなく「発見」のツール', color=WHITE, fontsize=24,
          ha='center', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/11_knn_prediction/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
