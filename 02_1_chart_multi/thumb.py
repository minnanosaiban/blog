"""
連載07 EDINET/TDnet取得とパース サムネイル生成
出力: docs/blog/posts/img/02_collect_other_data/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 1-2', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'EDINET', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.text(0.66, 0.69, '/TDnet', color=SOFT, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '株価以外のデータを', color=BLUE_L, fontsize=33, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '3 ソースから集める', color=WHITE, fontsize=33, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.06, 0.50, 0.80], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

# ===== 3つの無料ソース タイトル =====
ax_r.text(50, 94, '3 つの無料ソース', color=BLUE_L, fontsize=30,
          ha='center', va='center', fontweight='bold', style='italic')

# ===== 取得元ボックス（取得元名 ＋ 取れるデータ）=====
# (box下端y, 取得元名, 取れるデータ, アクセント色)
sources = [
    (60, '金融庁 EDINET',  '有報（XBRL）',     GREEN),
    (33, '東証 TDnet',     '決算短信・発表日',  BLUE_L),
    (6,  '証券会社アプリ',   '業績指標（CSV）',   SOFT),
]
for y, name, data, col in sources:
    ax_r.add_patch(patches.FancyBboxPatch(
        (3, y), 94, 20,
        boxstyle='round,pad=1.2',
        facecolor=MUTED_BG, edgecolor=col, linewidth=2.2
    ))
    # 左アクセントバー
    ax_r.add_patch(patches.Rectangle((7, y + 5), 2.2, 10, facecolor=col, linewidth=0))
    # 取得元名（左）
    ax_r.text(13, y + 10, name, color=WHITE, fontsize=24,
              ha='left', va='center', fontweight='bold')
    # 取れるデータ（右）
    ax_r.text(94, y + 10, data, color=col, fontsize=24,
              ha='right', va='center', fontweight='bold')

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/02_collect_other_data/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
