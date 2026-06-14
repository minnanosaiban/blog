"""
番外編A 超短期の統計検証 サムネイル生成
出力: docs/blog/posts/img/16_intraday_stats/00_thumbnail.png
"""
import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

BG = '#0d1b2a'
BLUE_L = '#5fa8e5'
GREEN = '#22c55e'
GOLD = '#d4a017'
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
ax_l.text(0.110, 0.902, '番外編 A', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.70, '超短期の', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.55, 'エッジ検証', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.45), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.35, '5分足×コスト控除後、', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.24, '残るシグナルは？', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# 右: エッジ vs コストの壁（横棒 2 本 + コスト帯）
ax_r = fig.add_axes([0.50, 0.14, 0.46, 0.68], facecolor=BG)
ax_r.set_xlim(0, 28)
ax_r.set_ylim(-0.7, 1.7)
ax_r.axis('off')

# コスト帯 5〜10bps（薄く・破線のみ強調）
ax_r.axvspan(5, 10, color=GOLD, alpha=0.08, zorder=0)
ax_r.plot([5, 5], [-0.55, 1.38], color=GOLD, linewidth=1.8, linestyle='--', alpha=0.9)
ax_r.plot([10, 10], [-0.55, 1.38], color=GOLD, linewidth=1.8, linestyle='--', alpha=0.9)
ax_r.text(7.5, 1.48, 'コストの壁 5〜10bps', color=GOLD, fontsize=22,
          ha='center', va='bottom', fontweight='bold')

bars = [
    ('テクニカル系', 0.3, BLUE_L, 0.85),
    ('場中開示ドリフト', 23.0, GREEN, -0.05),
]
for label, v, color, ypos in bars:
    ax_r.barh(ypos, v, height=0.4, color=color, alpha=0.95, zorder=3)
    ax_r.text(0.3, ypos + 0.34, label, color=color, fontsize=24,
              ha='left', va='center', fontweight='bold', zorder=4)
    ax_r.text(v + 0.5, ypos, f'+{v:.1f}bps', color=color, fontsize=24,
              ha='left', va='center', fontweight='bold', zorder=4)

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/16_intraday_stats/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
