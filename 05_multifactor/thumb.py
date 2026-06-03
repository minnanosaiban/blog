"""
連載02 マルチファクタースコアボード サムネイル生成
出力: docs/blog/posts/img/05_multifactor_scoreboard/00_thumbnail.png
サイズ: 1280x670 px（Note 推奨 16:9）
実行: python docs/blog/scripts/thumb_02_multifactor.py
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

rcParams['font.family'] = 'Noto Sans JP'
rcParams['axes.unicode_minus'] = False

# ---- カラー ----
BG     = '#0d1b2a'
BLUE_L = '#5fa8e5'
GREEN  = '#22c55e'
WHITE  = '#f5f8fc'
SOFT   = '#b5c4d6'

DPI = 100
fig = plt.figure(figsize=(12.80, 6.70), dpi=DPI, facecolor=BG)

# ===== 左エリア（タイトル）画面幅の 44% =====
ax_l = fig.add_axes([0.0, 0.0, 0.44, 1.0], facecolor=BG)
ax_l.axis('off')
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)

# 連載番号バー
ax_l.add_patch(patches.Rectangle(
    (0.07, 0.875), 0.018, 0.055, facecolor=BLUE_L, linewidth=0
))
ax_l.text(0.110, 0.902, '連載 2-2', color=BLUE_L,
          fontsize=24, va='center', ha='left', fontweight='bold')

# タイトル
ax_l.text(0.07, 0.69, 'マルチ', color=WHITE,
          fontsize=72, va='center', ha='left', fontweight='bold')
ax_l.text(0.60, 0.69, 'ファクタ', color=WHITE,
          fontsize=36, va='center', ha='left', fontweight='bold')

# 区切り線
ax_l.set_xlim(0, 1)
ax_l.set_ylim(0, 1)
ax_l.add_patch(patches.Rectangle((0.07, 0.578), 0.90, 0.004, facecolor=BLUE_L, linewidth=0, alpha=0.6))

# キャッチコピー
ax_l.text(0.07, 0.48, '複数指標を', color=BLUE_L,
          fontsize=36, va='center', ha='left', fontweight='bold')
ax_l.text(0.07, 0.37, '統合スコアで評価する', color=WHITE,
          fontsize=36, va='center', ha='left', fontweight='bold')

# 英語フルネーム

# ===== 右エリア（レーダーチャート）=====
factors = ['ROE 成長', 'PEG 割安', 'モメンタム', '市場需給', '配当利回', '財務安全', '決算品質']
scores  = [85, 72, 68, 71, 55, 62, 78]

N = len(factors)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles_closed = angles + [angles[0]]
scores_closed = scores + [scores[0]]

ax_r = fig.add_axes([0.53, 0.19, 0.36, 0.60], projection='polar', facecolor=BG)

# ROE 成長を頂点（12時）→時計回り
ax_r.set_theta_offset(np.pi / 2)
ax_r.set_theta_direction(-1)

# グリッドリング（20 / 40 / 60 / 80 / 100）
for r in [20, 40, 60, 80, 100]:
    ring_x = np.linspace(0, 2 * np.pi, 360)
    ax_r.plot(ring_x, [r] * 360, color='#2a3f55', linewidth=0.8)

# スポーク（各因子軸）
for angle in angles:
    ax_r.plot([angle, angle], [0, 100], color='#2a3f55', linewidth=0.8)

# 塗り + 輪郭
ax_r.fill(angles_closed, scores_closed, color=BLUE_L, alpha=0.25)
ax_r.plot(angles_closed, scores_closed, color=BLUE_L, linewidth=2.5)

# 各頂点ドット（スコア数値は24pt未満になるため削除）
for angle, score in zip(angles, scores):
    ax_r.scatter(angle, score, s=80, color=GREEN, zorder=5, edgecolors='none')

# 因子ラベル（外周）
ax_r.set_xticks(angles)
ax_r.set_xticklabels(factors, color=WHITE, fontsize=24, fontweight='bold')
ax_r.tick_params(axis='x', pad=17)

# 内側の数値ラベルを非表示
ax_r.set_yticks([])
ax_r.set_ylim(0, 125)

# 外枠・背景を透明に
ax_r.spines['polar'].set_visible(False)
ax_r.set_facecolor(BG)

# 総合スコアを中心に表示
ax_r.text(0, 0, '71', color=WHITE, fontsize=32, fontweight='bold',
          ha='center', va='center')
ax_r.text(0, -28, 'Total Score', color=SOFT, fontsize=24,
          ha='center', va='center')

# 出力
OUT = r"C:/minnanosaiban/hotline/docs/blog/posts/img/05_multifactor_scoreboard/00_thumbnail.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=DPI, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
plt.close()
print(f'Saved -> {OUT}')
