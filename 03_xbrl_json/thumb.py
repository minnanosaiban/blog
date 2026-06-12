"""
連載06 XBRLとは何か サムネイル生成
出力: docs/blog/posts/img/03_xbrl_to_json/00_thumbnail.png
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
ax_l.text(0.110, 0.902, '連載 1-3', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, 'XBRL→JSON', color=WHITE, fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '有報・決算短信を', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '分析に使えるかたちに', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

ax_r = fig.add_axes([0.46, 0.10, 0.50, 0.80], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')

# 全ボックス共通サイズ（幅を統一）。左端をタイトルから離すため右寄せに配置
BOX_W, BOX_H = 24, 28

# ===== 左: EDINET / TDnet（2ソース） =====
for cx, cy, label, color, sub in [
    (24, 65, 'EDINET', BLUE_L, '有報'),
    (24, 33, 'TDnet',  GREEN,  '決算短信'),
]:
    ax_r.add_patch(patches.FancyBboxPatch((cx-BOX_W/2, cy-BOX_H/2), BOX_W, BOX_H,
                                          boxstyle='round,pad=1',
                                          facecolor=color, edgecolor='none', alpha=0.25))
    ax_r.text(cx, cy+5, label, color=WHITE, fontsize=24, ha='center', va='center', fontweight='bold')
    ax_r.text(cx, cy-7, sub,   color=SOFT,  fontsize=24, ha='center', va='center')

# ===== 中央: XBRLパース =====
ax_r.add_patch(patches.FancyBboxPatch((55-BOX_W/2, 49-BOX_H/2), BOX_W, BOX_H,
                                      boxstyle='round,pad=1',
                                      facecolor=BLUE_L, edgecolor='none', alpha=0.25))
ax_r.text(55, 54, 'XBRL', color=WHITE, fontsize=24, ha='center', va='center', fontweight='bold')
ax_r.text(55, 42, 'パース', color=SOFT, fontsize=24, ha='center', va='center')

# ===== 右: JSON =====
ax_r.add_patch(patches.FancyBboxPatch((86-BOX_W/2, 49-BOX_H/2), BOX_W, BOX_H,
                                      boxstyle='round,pad=1',
                                      facecolor=GREEN, edgecolor='none', alpha=0.25))
ax_r.text(86, 49, 'JSON', color=WHITE, fontsize=24, ha='center', va='center', fontweight='bold')

# ===== 扇形矢印（EDINET/TDnet → パース） =====
ax_r.annotate('', xy=(43, 53), xytext=(36, 62),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))
ax_r.annotate('', xy=(43, 45), xytext=(36, 36),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))

# ===== 矢印（パース → JSON） =====
ax_r.annotate('', xy=(74, 49), xytext=(67, 49),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/03_xbrl_to_json/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
