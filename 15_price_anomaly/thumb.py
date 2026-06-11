"""
連載 3-6 値動きの異常検知（共動の崩れ）サムネイル生成
出力: docs/blog/posts/img/15_price_anomaly/00_thumbnail.png
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
RED = '#ef4444'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ── 左：タイトル ───────────────────────────────
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 3-6', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'PCA 異常検知', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '「共動の崩れ」で', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '突発材料を検出', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# ── 右：束で動く仲間（灰）＋ 1 本だけ急変（赤）──
ax_r = fig.add_axes([0.46, 0.10, 0.50, 0.80], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

x = np.linspace(4, 96, 240)
common = 46 + 7 * np.sin((x - 4) / 26)          # 全員が乗る共通の波
rng = np.random.default_rng(3)

# 仲間（ピア）＝ 束で一緒に動く
for k, off in enumerate([-7, -3.5, 0, 3.5, 7]):
    y = common + off + 1.0 * np.sin(x / 5.0 + k)
    ax_r.plot(x, y, color=SOFT, alpha=0.5, lw=2.2, solid_capstyle='round')

# 異常銘柄＝ 途中までは仲間と一緒、ある日から急変
brk = 66
ya = common + 0.0
mask = x > brk
ya = ya.copy()
ya[mask] = ya[mask] + (x[mask] - brk) * 1.75
ax_r.plot(x, ya, color=RED, lw=3.6, solid_capstyle='round', zorder=5)

# 共動が崩れた日
ax_r.axvline(brk, color=WHITE, lw=1.0, ls=(0, (2, 3)), alpha=0.35)
ax_r.scatter([x[-1]], [ya[-1]], s=120, color=RED, edgecolors=WHITE, linewidths=1.4, zorder=6)

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/15_price_anomaly/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
