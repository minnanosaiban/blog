"""
連載 3-5 値動きクラスタリング サムネイル生成
出力: docs/blog/posts/img/14_price_clustering/00_thumbnail.png
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
GREEN = '#22c55e'
TEAL = '#22d4a8'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'
DIM = '#1b3147'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ── 左：タイトル ───────────────────────────────
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 3-5', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, '階層型', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.text(0.60, 0.69, 'クラスタリング', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '値動きの相関で', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '再現する業界地図', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# ── 右：ブロック対角の相関ヒートマップ（＝クラスタ）──
ax_r = fig.add_axes([0.52, 0.08, 0.44, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

n = 12
m0, m1 = 12, 88          # グリッドの描画範囲
cell = (m1 - m0) / n
# 対角ブロック（クラスタ）＝ 連続インデックスのまとまりと色
clusters = [(range(0, 4), BLUE_L), (range(4, 9), GREEN), (range(9, 12), TEAL)]
cl_of = {}
for idxs, col in clusters:
    for i in idxs:
        cl_of[i] = col

rng = np.random.default_rng(5)
for i in range(n):
    for j in range(n):
        x = m0 + j * cell
        y = m1 - (i + 1) * cell          # 上から下へ
        same = cl_of[i] == cl_of[j]
        if same:
            col = cl_of[i]
            a = 0.95 if i == j else float(rng.uniform(0.55, 0.85))
        else:
            col = DIM
            a = float(rng.uniform(0.18, 0.35))
        ax_r.add_patch(patches.Rectangle((x, y), cell * 0.92, cell * 0.92,
                                         facecolor=col, edgecolor=BG, linewidth=1.0, alpha=a))

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/14_price_clustering/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
