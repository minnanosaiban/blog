"""
連載2-4 予想検証 サムネイル生成
出力: docs/blog/posts/img/07_triangulation/00_thumbnail.png

レイアウト: 03（XBRL→JSON）と同じボックス・フロー型。
  業績 / ガイダンス / コンセンサス（3 入力）→ 予想検証 → ★上方修正 / ⚠達成困難（2 判定）
最小フォント 24pt（入りきらないサブ文字＝確定/会社予想/アナリスト等は削除）。
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
TEAL = '#22d4a8'
RED = '#e07a7a'
MUTED_BG = '#1a2535'
WHITE = '#f5f8fc'
SOFT = '#b5c4d6'

FS = 24  # 最小フォント（全ラベル共通）

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ===== 左: タイトルブロック（03 と同じ作法） =====
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

ax_l.add_patch(patches.Rectangle((0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0))
ax_l.text(0.110, 0.902, '連載 2-4', color=BLUE_L, fontsize=24, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.69, '予想 × 業績', color=WHITE, fontsize=60, va='center', ha='left', fontweight='bold')
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.85, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))
ax_l.text(0.07, 0.48, '予想のズレを', color=BLUE_L, fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '見抜く', color=WHITE, fontsize=36, va='center', ha='left', fontweight='bold')

# ===== 右: パイプライン図 =====
ax_r = fig.add_axes([0.46, 0.08, 0.52, 0.84], facecolor=BG)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(0, 100)
ax_r.axis('off')


def box(cx, cy, w, h, color, label, fs=FS):
    ax_r.add_patch(patches.FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                                          boxstyle='round,pad=1',
                                          facecolor=color, edgecolor='none', alpha=0.25))
    ax_r.text(cx, cy, label, color=WHITE, fontsize=fs, ha='center', va='center', fontweight='bold')


# 3 入力（左・縦並び）― サブ文字は削除し主ラベルのみ 24pt
IN_W, IN_H = 34, 21
box(18, 82, IN_W, IN_H, GREEN,  '業績')
box(18, 50, IN_W, IN_H, BLUE_L, 'ガイダンス')
box(18, 18, IN_W, IN_H, TEAL,   'コンセンサス')

# 予想検証（中央・2 行）
ax_r.add_patch(patches.FancyBboxPatch((52-15/2, 50-30/2), 15, 30,
                                      boxstyle='round,pad=1',
                                      facecolor=BLUE_L, edgecolor='none', alpha=0.25))
ax_r.text(52, 57, '予想', color=WHITE, fontsize=FS, ha='center', va='center', fontweight='bold')
ax_r.text(52, 43, '検証', color=WHITE, fontsize=FS, ha='center', va='center', fontweight='bold')

# 2 判定（右・縦並び）
box(84, 68, 30, 21, GREEN, '★ 上方修正')
box(84, 32, 30, 21, RED,   '⚠ 達成困難')

# 扇形矢印（3 入力 → 予想検証）
for ytxt, yend in [(78, 57), (50, 50), (22, 43)]:
    ax_r.annotate('', xy=(43.5, yend), xytext=(36, ytxt),
                  arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))

# 分岐矢印（予想検証 → 2 判定）
ax_r.annotate('', xy=(68, 66), xytext=(60.5, 55),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))
ax_r.annotate('', xy=(68, 34), xytext=(60.5, 45),
              arrowprops=dict(arrowstyle='->', color=SOFT, lw=2, alpha=0.7))

OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/07_triangulation/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
