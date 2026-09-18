"""
動画からフレームを抽出し、WSL2(Ubuntu)にインストールしたCOLMAP(Linux版)へ渡して
高品質な3D点群(スパース点群、可能なら密なMVS点群)を生成する。

背景:
Windows版COLMAPはこのマシンのスマートアプリコントロールに実行をブロックされるため、
WSL2上のCOLMAP(`wsl`コマンド経由で呼び出す)を使う方式にしている。
WSL側のCOLMAPはCUDA無しビルド(`apt install colmap`)のため、sparse(疎点群・カメラ姿勢の
Incremental SfM)は動くが、dense(MVS密点群, patch_match_stereo)はGPU必須のため失敗する。
denseがどうしても必要な場合は、WSL内でCOLMAPをCUDA有効でソースからビルドし直すこと。

epora.py/bandled.py/pointcloud.pyの自作パイプライン(2view限定・非calibrated)と違い、
COLMAPは動画中の全フレームをまとめてIncremental SfMにかけ、カメラの内部パラメータも
自動推定した上で、スケール・姿勢が一貫した点群を作る。
"""

import os
import subprocess

import cv2

video_path = "20260902_022515000_iOS.MOV"
workspace_dir = os.path.abspath("colmap_workspace")

frame_step = 5  # 動画から何フレームおきに画像を抽出するか(小さいほど密で高品質だが遅い)
quality = "high"  # low / medium / high / extreme (automatic_reconstructorの品質設定)
dense = True  # Trueなら密な点群(MVS)も試みる。CUDA無しビルドだと失敗する可能性がある


def extract_frames(video_path, images_dir, frame_step):
    """動画からframe_stepおきにフレームを抽出し、カラーのままJPEGとして保存する。"""
    os.makedirs(images_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"動画を開けませんでした: {video_path}")

    idx = 0
    saved = 0
    ok, frame = cap.read()
    while ok:
        if idx % frame_step == 0:
            cv2.imwrite(os.path.join(images_dir, f"frame_{idx:05d}.jpg"), frame)
            saved += 1
        ok, frame = cap.read()
        idx += 1
    cap.release()

    print(f"動画の{idx}フレーム中{saved}枚を抽出しました: {images_dir}")
    if saved < 10:
        raise RuntimeError("抽出できた画像が少なすぎます(10枚未満)。frame_stepを小さくしてください。")
    return saved


def to_wsl_path(windows_path):
    """WindowsパスをWSL内のパス(/mnt/c/...)に変換する。"""
    result = subprocess.run(
        ["wsl", "wslpath", "-a", windows_path.replace("\\", "/")],
        capture_output=True, text=True, check=True)
    return result.stdout.strip()


def run_in_wsl(args):
    cmd = ["wsl", "--"] + args
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    images_dir = os.path.join(workspace_dir, "images")
    sparse_dir = os.path.join(workspace_dir, "sparse")
    dense_dir = os.path.join(workspace_dir, "dense")

    extract_frames(video_path, images_dir, frame_step)

    workspace_wsl = to_wsl_path(workspace_dir)
    images_wsl = to_wsl_path(images_dir)

    returncode = run_in_wsl([
        "colmap", "automatic_reconstructor",
        "--workspace_path", workspace_wsl,
        "--image_path", images_wsl,
        "--data_type", "video",      # 連番動画フレーム向けにsequential matcherを使わせる
        "--quality", quality,
        "--single_camera", "1",      # 同一カメラの動画なので内部パラメータを共有させる
        "--sparse", "1",
        "--dense", "1" if dense else "0",
        "--use_gpu", "0",            # WSL版COLMAPはCUDA無しビルドのため常にCPU動作
    ])

    if returncode != 0:
        print(f"\nCOLMAPがエラー終了しました(終了コード {returncode})。上のログを確認してください。")

    sparse_model = os.path.join(sparse_dir, "0")
    if os.path.isdir(sparse_model):
        print(f"\nスパース点群(カメラ姿勢・疎な3D点、COLMAP形式)を生成しました: {sparse_model}")
    else:
        print(f"\n警告: {sparse_model} が見つかりません。")

    fused_path = os.path.join(dense_dir, "fused.ply")
    if os.path.exists(fused_path):
        print(f"密な点群(MVS)を生成しました: {fused_path}")
    elif dense:
        print(f"\n{fused_path} が見つかりません。WSL版COLMAPはCUDA無しビルドのため"
              "dense(patch_match_stereo)は失敗した可能性があります。"
              "sparseのみで良ければdense=Falseにしてください。")
