"""
COLMAPのスパース点群と、3DGS学習結果(.splatに変換済みのモデル、またはPLY)を
オフスクリーンでレンダリングしてプレビュー画像を保存する。
WSLg経由のインタラクティブ表示がうまくいかない環境でも、画像としての確認・記事用の
スクリーンショット取得に使える。
"""

import numpy as np
import open3d as o3d

sparse_ply = "../../colmap_workspace/sparse_points.ply"
output_image = "../images/03_sparse_pointcloud.png"

pcd = o3d.io.read_point_cloud(sparse_ply)
print(f"点数: {len(pcd.points)}")

vis = o3d.visualization.Visualizer()
vis.create_window(visible=False, width=1280, height=800)
vis.add_geometry(pcd)

opt = vis.get_render_option()
opt.background_color = np.asarray([0.05, 0.05, 0.08])
opt.point_size = 3.0

ctr = vis.get_view_control()
vis.poll_events()
vis.update_renderer()
ctr.set_zoom(0.35)

vis.poll_events()
vis.update_renderer()
vis.capture_screen_image(output_image, do_render=True)
vis.destroy_window()
print(f"保存しました: {output_image}")
