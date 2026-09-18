"""
COLMAPの再構成結果を使って、WSL2上の3D Gaussian Splatting
(graphdeco-inria/gaussian-splatting)を学習し、3DGSモデル(ガウシアン点群 .ply)を生成する。

事前準備(WSL側に用意済み):
- ~/gaussian-splatting (リポジトリ本体 + submodule、CUDA拡張ビルド済み)
- ~/gaussian-splatting/venv (torch+CUDA対応のvenv)

3D Gaussian Splattingは歪み補正済み(PINHOLE/SIMPLE_PINHOLEカメラモデル)の
データセットしか読めない。colmap_workspace/sparse/0 は歪み補正前(distorted)なので、
MVS用に colmap_reconstruct.py が作った colmap_workspace/dense/
(colmap image_undistorterで歪み補正済み、sparse/0/以下に配置済み)を使う。
"""

import os
import subprocess

workspace_dir = os.path.abspath(os.path.join("colmap_workspace", "dense"))
model_output_dir = os.path.abspath("gaussian_splat_output")

iterations = 30000  # 学習反復数(公式デフォルト)
repo_dir_wsl = "~/gaussian-splatting"
venv_python_wsl = "~/gaussian-splatting/venv/bin/python"


def to_wsl_path(windows_path):
    """WindowsパスをWSL内のパス(/mnt/c/...)に変換する。"""
    result = subprocess.run(
        ["wsl", "wslpath", "-a", windows_path.replace("\\", "/")],
        capture_output=True, text=True, check=True)
    return result.stdout.strip()


if __name__ == "__main__":
    if not os.path.isdir(os.path.join(workspace_dir, "sparse", "0")):
        raise FileNotFoundError(
            f"{workspace_dir}/sparse/0 が見つかりません。先に colmap_reconstruct.py (image_undistorter) を実行してください。")

    os.makedirs(model_output_dir, exist_ok=True)

    source_path = to_wsl_path(workspace_dir)
    model_path = to_wsl_path(model_output_dir)

    cmd = [
        "wsl", "--", "bash", "-lc",
        f"cd {repo_dir_wsl} && {venv_python_wsl} train.py "
        f"-s {source_path} -m {model_path} --iterations {iterations} --eval"
    ]
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"3DGS学習が失敗しました(終了コード {result.returncode})")

    final_ply = os.path.join(model_output_dir, "point_cloud", f"iteration_{iterations}", "point_cloud.ply")
    print(f"\n3DGSモデルを {model_output_dir} に保存しました。")
    print(f"ガウシアン点群ファイル: {final_ply}")
    print("(通常のOpen3D等ではなく、3DGS対応ビューア[SIBR_viewers等]で開く必要があります)")
