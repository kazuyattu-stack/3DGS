"""パイプライン全体の流れを示す簡単な図を作る。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties

# Windows標準の日本語フォントを指定
jp_font = FontProperties(fname=r"C:\Windows\Fonts\meiryo.ttc")

steps = [
    "iPhone動画\n(.MOV)",
    "フレーム抽出\n(OpenCV)",
    "COLMAP\nSfM(疎点群・\nカメラ姿勢推定)",
    "COLMAP\nMVS(歪み補正・\n密ステレオ)",
    "3D Gaussian\nSplatting学習\n(WSL2+CUDA)",
    "WebGL\nビューアで確認\n(ブラウザ)",
]

fig, ax = plt.subplots(figsize=(14, 3.2))
ax.set_xlim(0, len(steps))
ax.set_ylim(0, 1)
ax.axis("off")
fig.patch.set_facecolor("white")

box_w = 0.82
colors = ["#4C72B0", "#55A868", "#C44E52", "#C44E52", "#8172B2", "#CCB974"]

for i, (step, color) in enumerate(zip(steps, colors)):
    x = i + (1 - box_w) / 2
    rect = mpatches.FancyBboxPatch(
        (x, 0.25), box_w, 0.5,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=color, edgecolor="none", alpha=0.9
    )
    ax.add_patch(rect)
    ax.text(i + 0.5, 0.5, step, ha="center", va="center",
             fontsize=11, color="white", fontproperties=jp_font, linespacing=1.4)
    if i < len(steps) - 1:
        ax.annotate("", xy=(i + 1 + (1 - box_w) / 2 - 0.02, 0.5), xytext=(i + 1 - (1 - box_w) / 2 + 0.02, 0.5),
                     arrowprops=dict(arrowstyle="->", color="#333333", lw=2))

plt.tight_layout()
plt.savefig("../images/pipeline_overview.png", dpi=150, facecolor="white")
print("saved pipeline_overview.png")
