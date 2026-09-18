"""レンダリング画像の余白を自動検出してクロップ・拡大する。"""
import numpy as np
from PIL import Image

path = "../images/03_sparse_pointcloud.png"
img = Image.open(path)
arr = np.array(img.convert("L"))

# 背景(暗い色)より明るい画素の範囲を探す
mask = arr > 30
ys, xs = np.where(mask)
pad = 30
x0, x1 = np.percentile(xs, 0.5) - pad, np.percentile(xs, 99.5) + pad
y0, y1 = np.percentile(ys, 0.5) - pad, np.percentile(ys, 99.5) + pad
x0, y0 = max(int(x0), 0), max(int(y0), 0)
x1, y1 = min(int(x1), arr.shape[1]), min(int(y1), arr.shape[0])

cropped = img.crop((x0, y0, x1, y1))
cropped.save(path)
print(f"cropped to {cropped.size}")
