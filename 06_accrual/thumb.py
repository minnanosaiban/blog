"""
連載10 アクルーアル分析 サムネイル生成
出力: docs/blog/posts/img/06_accrual_analysis/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 2-3', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'アクルーアル', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '利益の', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '現金化率を検証', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.10, 0.50, 0.82], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(-28, 140)
ax_r.axis('off')

# 見出し（右上・棒と重ならない位置）
ax_r.text(50, 137, 'ENEOS 2022 ピーク利益', color=SOFT, fontsize=24,
          ha='center', va='top', fontweight='bold')

# ベースライン
ax_r.plot([12, 88], [0, 0], color=SOFT, linewidth=1.2, alpha=0.4)

# 純利益 vs 営業CF を細めの 2 本で直接対比
BAR_W = 15
bars = [
    (33, 100, '純利益', '5,371 億', BLUE_L, '100%'),
    (63, 39,  '営業CF', '2,095 億', GREEN,  '39%'),
]
for x, h, cat, amt, color, pct in bars:
    ax_r.add_patch(patches.Rectangle((x - BAR_W / 2, 0), BAR_W, h,
                   facecolor=color, edgecolor='none', alpha=0.22))
    ax_r.add_patch(patches.Rectangle((x - BAR_W / 2, 0), BAR_W, h,
                   facecolor='none', edgecolor=color, alpha=0.85, linewidth=2.5))
    ax_r.text(x, h + 4, pct, color=color, fontsize=30,
              ha='center', va='bottom', fontweight='bold')
    ax_r.text(x, -7, cat, color=WHITE, fontsize=24,
              ha='center', va='top', fontweight='bold')

# 利益と CF の落差 = 61% は現金化されず
ax_r.plot([33, 82], [100, 100], color=SOFT, lw=1.0, alpha=0.4,
          linestyle=(0, (4, 3)))
ax_r.plot([63, 82], [39, 39], color=SOFT, lw=1.0, alpha=0.4,
          linestyle=(0, (4, 3)))
ax_r.annotate('', xy=(82, 100), xytext=(82, 39),
              arrowprops=dict(arrowstyle='<->', color=WHITE, lw=2))
ax_r.text(85, 69, '61%', color=WHITE, fontsize=24,
          ha='left', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/06_accrual_analysis/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
