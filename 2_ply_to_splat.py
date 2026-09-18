"""
3D Gaussian Splattingが出力したPLY(gaussian_splat_output/point_cloud/.../point_cloud.ply)を、
antimatter15/splat互換の軽量な.splatバイナリ形式に変換する(ベクトル化版、高速)。

このスクリプトの変換ロジック(position/scale/color/rotationの計算式)は、
antimatter15/splat (https://github.com/antimatter15/splat) の convert.py を
numpyでベクトル化して書き直したものです。

--- 元コードのライセンス表示 (MIT License) ---
Copyright (c) 2023 Kevin Kwok

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys

import numpy as np
from plyfile import PlyData

input_path = sys.argv[1] if len(sys.argv) > 1 else "../gaussian_splat_output/point_cloud/iteration_30000/point_cloud.ply"
output_path = sys.argv[2] if len(sys.argv) > 2 else "model.splat"

SH_C0 = 0.28209479177387814

print(f"読み込み中: {input_path}")
plydata = PlyData.read(input_path)
vert = plydata["vertex"]
n = len(vert)
print(f"点数: {n}")

position = np.stack([vert["x"], vert["y"], vert["z"]], axis=1).astype(np.float32)
scales = np.exp(np.stack([vert["scale_0"], vert["scale_1"], vert["scale_2"]], axis=1).astype(np.float32))
opacity = 1.0 / (1.0 + np.exp(-vert["opacity"].astype(np.float32)))

# 表示優先度(大きく不透明なガウシアンを先に)でソート
sort_key = -(scales[:, 0] + scales[:, 1] + scales[:, 2]) * opacity
order = np.argsort(sort_key)

position = position[order]
scales = scales[order]
opacity = opacity[order]

color = np.stack([
    0.5 + SH_C0 * vert["f_dc_0"][order],
    0.5 + SH_C0 * vert["f_dc_1"][order],
    0.5 + SH_C0 * vert["f_dc_2"][order],
], axis=1).astype(np.float32)
color_bytes = np.concatenate([color, opacity[:, None]], axis=1)
color_bytes = (color_bytes * 255).clip(0, 255).astype(np.uint8)

rot = np.stack([vert["rot_0"], vert["rot_1"], vert["rot_2"], vert["rot_3"]], axis=1).astype(np.float32)[order]
rot = rot / np.linalg.norm(rot, axis=1, keepdims=True)
rot_bytes = (rot * 128 + 128).clip(0, 255).astype(np.uint8)

# 1レコード32バイト(位置12B + スケール12B + 色4B + 回転4B)の構造化配列にまとめて一括書き出し
record_dtype = np.dtype([
    ("position", "<f4", 3),
    ("scales", "<f4", 3),
    ("color", "u1", 4),
    ("rot", "u1", 4),
])
records = np.empty(n, dtype=record_dtype)
records["position"] = position
records["scales"] = scales
records["color"] = color_bytes
records["rot"] = rot_bytes

records.tofile(output_path)

print(f"保存しました: {output_path} ({n * 32} bytes)")
