"""
連載13 CARイベントスタディ サムネイル生成
出力: docs/blog/posts/img/09_car_event_study/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 2-7', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'CARイベント', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, 'イベント直後の', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '超過リターンを検出', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.12, 0.50, 0.78], facecolor=BG)
ax_r.set_xlim(-7, 24)
ax_r.set_ylim(-20, 10)
ax_r.axis('off')

import numpy as np
t_before = np.linspace(-6, 0, 30)
t_after  = np.linspace(0, 22, 80)
car_after = -13.89 * (1 - np.exp(-0.18 * t_after))

# 発表前（水平）
ax_r.plot(t_before, np.zeros_like(t_before), color=SOFT, linewidth=2.5, alpha=0.7)
# 発表後（下落）
ax_r.plot(t_after, car_after, color='#ff6b6b', linewidth=3)
ax_r.fill_between(t_after, 0, car_after, color='#ff6b6b', alpha=0.15)

# ベースライン
ax_r.axhline(0, color=SOFT, linewidth=1, alpha=0.3)

# イベントマーカー
ax_r.axvline(0, color=WHITE, linewidth=2, linestyle='--', alpha=0.65)
ax_r.scatter([0], [0], s=120, color=WHITE, zorder=5)
ax_r.text(0, 2, '決算発表  t=0', color=WHITE, fontsize=24,
          ha='center', va='bottom', fontweight='bold')

# CAR値アノテーション
ax_r.annotate('', xy=(21, car_after[-1]), xytext=(21, 0),
              arrowprops=dict(arrowstyle='<->', color='#ff6b6b', lw=2))
ax_r.text(22.5, car_after[-1]/2, 'CAR\n−13.89%', color='#ff6b6b', fontsize=24,
          ha='left', va='center', fontweight='bold')

# 銘柄
ax_r.text(-4, 8, 'ENEOS 2025/3期', color=SOFT, fontsize=24,
          ha='center', va='center')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/09_car_event_study/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
