"""
番外編B 超短期ML検証 サムネイル生成
出力: docs/blog/posts/img/17_intraday_ml/00_thumbnail.png
"""
import os
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

BG = '#0d1b2a'
BLUE_L = '#5fa8e5'
GREEN = '#22c55e'
RED = '#ff6b6b'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '番外編 B', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'LightGBM', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '「次の5分」の並べ替えは', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, 'できる、でも獲れない', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# 右: 確信度十分位の階段（実測値）
res = json.loads(Path(r"C:\stock_analysis\data\blog21\results_summary.json")
                 .read_text(encoding="utf-8"))
dec = res["decile_table"]
keys = sorted(dec.keys(), key=int)
vals = [dec[k]["mean_bps"] for k in keys]

ax_r = fig.add_axes([0.50, 0.16, 0.46, 0.62], facecolor=BG)
ax_r.set_xlim(-0.7, 9.7)
vmax = max(abs(v) for v in vals) * 1.45
ax_r.set_ylim(-vmax, vmax)
ax_r.axis('off')
ax_r.axhline(0, color=SOFT, linewidth=1.2, alpha=0.6)
for i, v in enumerate(vals):
    color = RED if v < 0 else GREEN
    ax_r.bar(i, v, width=0.62, color=color, alpha=0.92)
ax_r.text(0, vmax * 0.82, '確信度 低', color=RED, fontsize=22,
          ha='left', va='center', fontweight='bold')
ax_r.text(9, vmax * 0.82, '高', color=GREEN, fontsize=22,
          ha='right', va='center', fontweight='bold')
ax_r.text(4.5, -vmax * 0.92, '十分位はきれいに単調 ― でも端でも +0.2bps',
          color=SOFT, fontsize=20, ha='center', va='center')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/17_intraday_ml/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
