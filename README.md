iPhoneで撮った動画から、COLMAPと3D Gaussian Splattingを使って3Dモデルを作り、
ブラウザで確認するまでのパイプラインです。

## 使い方

```bash
# 1. 動画からフレーム抽出 + COLMAPでカメラ姿勢・スパース点群を推定
python scripts/1_colmap_reconstruct.py

# 2. 3D Gaussian Splattingで学習
python scripts/3_train_3dgs.py

# 3. 結果を軽量な.splat形式に変換してブラウザで確認
python scripts/2_ply_to_splat.py <point_cloud.plyのパス> splat_viewer/model.splat
cd splat_viewer && python -m http.server 8080
# http://localhost:8080/ を開く
```

## 使っているOSS

- [COLMAP](https://github.com/colmap/colmap) — カメラ姿勢推定・3D復元(BSD-3-Clause)
- [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting) — ガウシアンスプラット学習(Inria/MPII、非商用研究ライセンス)
- [antimatter15/splat](https://github.com/antimatter15/splat) — WebGLビューア(MIT License)。`splat_viewer/`と`scripts/2_ply_to_splat.py`に一部コードを含む
