"""
連載01 株価取得 サムネイル生成
出力: docs/blog/posts/img/01_get_stock_prices/00_thumbnail.png
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
RED = '#ef5350'
MUTED_BG = '#1a2535'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ===== 左パネル: タイトル =====
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 1-1', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.66, '株価取得', color=WHITE, fontsize=66, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.548), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.45, 'CSVより処理の早い', color=BLUE_L, fontsize=29, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.34, 'parquet形式を利用', color=WHITE, fontsize=29, va='center', ha='left', fontweight='bold')

# ===== 右パネル: 5分足ローソク（イラスト） =====
ax_r = fig.add_axes([0.47, 0.13, 0.49, 0.72], facecolor=MUTED_BG)
ax_r.set_xlim(0, 13)
ax_r.set_ylim(4.1, 7.5)
ax_r.axis('off')

# 日付の縦境界線（午前=濃いめ / 午後=薄め を象徴）
for x, a in [(4.5, 0.30), (8.3, 0.18)]:
    ax_r.axvline(x, color=SOFT, alpha=a, lw=1.2)

# (open, high, low, close) ― 上昇=赤 / 下落=緑（日本式）
candles = [
    (5.0, 5.5, 4.7, 5.3), (5.3, 5.7, 5.1, 5.5), (5.5, 6.0, 5.4, 5.9),
    (5.9, 6.1, 5.3, 5.5), (5.5, 5.8, 4.9, 5.0), (5.0, 5.3, 4.6, 5.2),
    (5.2, 5.9, 5.1, 5.8), (5.8, 6.5, 5.7, 6.3), (6.3, 6.7, 6.0, 6.1),
    (6.1, 6.4, 5.8, 6.2), (6.2, 6.9, 6.1, 6.8), (6.8, 7.2, 6.6, 7.0),
]
for i, (o, h, l, c) in enumerate(candles):
    x = 1.2 + i * 0.95
    col = RED if c >= o else GREEN
    ax_r.plot([x, x], [l, h], color=col, lw=1.6, solid_capstyle='round')
    ax_r.add_patch(patches.Rectangle(
        (x - 0.28, min(o, c)), 0.56, abs(c - o) or 0.05,
        facecolor=col, edgecolor=col, linewidth=0,
    ))

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/01_get_stock_prices/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
