"""scripts/ フォルダの各スクリプトを解説するWord文書(script_explanation.docx)を作成する。"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

style = doc.styles["Normal"]
style.font.name = "Yu Gothic"
style.font.size = Pt(11)
rpr = style.element.get_or_add_rPr()
rFonts = rpr.find(qn("w:rFonts"))
if rFonts is None:
    rFonts = rpr.makeelement(qn("w:rFonts"), {})
    rpr.append(rFonts)
rFonts.set(qn("w:eastAsia"), "Yu Gothic")


def add_code_block(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9.5)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), "Consolas")
    return p


def add_note(text):
    p = doc.add_paragraph(text)
    p.runs[0].font.size = Pt(9.5)
    p.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    p.runs[0].italic = True


doc.add_heading("3DGSパイプライン スクリプト解説", level=0)
doc.add_paragraph(
    "3DGS_ガイド/scripts/ フォルダに入っている各スクリプトが、"
    "「何を」「どういう順番で」「どこでPythonを使い、どこでCOLMAP/3DGSの外部コマンドを呼んでいるか」"
    "をまとめた解説です。実際に動かす順番に並べています。"
)

# ==========================================
# 全体の実行順
# ==========================================
doc.add_heading("実行順序", level=1)
order_table = doc.add_table(rows=1, cols=3)
order_table.style = "Light Grid Accent 1"
hdr = order_table.rows[0].cells
hdr[0].text = "順番"
hdr[1].text = "スクリプト"
hdr[2].text = "実行場所"
for no, name, where in [
    ("1", "1_colmap_reconstruct.py", "Windows側のPythonから実行(内部でWSLのcolmapをsubprocess呼び出し)"),
    ("2", "2_ply_to_splat.py", "Windows側のPythonから実行"),
    ("3", "3_train_3dgs.py", "Windows側のPythonから実行(内部でWSLのtrain.pyをsubprocess呼び出し)"),
    ("-", "render_previews.py / crop_preview.py / make_pipeline_diagram.py", "ドキュメント用の画像を作るための補助スクリプト(パイプライン本体には不要)"),
]:
    cells = order_table.add_row().cells
    cells[0].text, cells[1].text, cells[2].text = no, name, where

doc.add_paragraph()
doc.add_paragraph(
    "ポイントは、「1」と「3」はどちらもWindows側のPythonスクリプトでありながら、"
    "内部で subprocess.run([\"wsl\", ...]) を使ってWSL2(Ubuntu)内のCOLMAP/3D Gaussian Splattingの"
    "実行ファイルを呼び出している、という二重構造になっていることです。"
    "これはWindowsネイティブ版COLMAPがこの環境で実行できなかったための構成です。"
)

# ==========================================
# 1_colmap_reconstruct.py
# ==========================================
doc.add_heading("1_colmap_reconstruct.py", level=1)
doc.add_paragraph("役割: 動画から静止画を抽出し、COLMAPでカメラ姿勢とスパース点群を推定する。")

doc.add_heading("① extract_frames() — Pythonの担当", level=2)
add_note("ここは純粋なPython(OpenCV)処理。外部コマンドは呼ばない。")
doc.add_paragraph(
    "cv2.VideoCapture で動画を1フレームずつ読み込み、frame_step 枚おきに間引いて "
    "JPEGとして images_dir に保存する。動画ファイルを直接扱えるのはこの関数だけで、"
    "これ以降の処理はすべて「画像ファイルの集まり」に対して行われる。"
)
add_code_block(
    "cap = cv2.VideoCapture(video_path)\n"
    "ok, frame = cap.read()\n"
    "while ok:\n"
    "    if idx % frame_step == 0:\n"
    "        cv2.imwrite(f\"{images_dir}/frame_{idx:05d}.jpg\", frame)\n"
    "    ok, frame = cap.read()\n"
    "    idx += 1"
)

doc.add_heading("② to_wsl_path() — PythonとWSLの橋渡し", level=2)
add_note("Pythonの中でWSLのコマンド(wslpath)を呼んでいる箇所。")
doc.add_paragraph(
    "Windows形式のパス(C:\\Users\\...)を、WSL側から見えるパス(/mnt/c/Users/...)に変換する。"
    "subprocess.run([\"wsl\", \"wslpath\", \"-a\", windows_path]) を実行し、"
    "その標準出力(WSL側のパス文字列)を受け取っているだけで、変換処理自体はWSL側のwslpathコマンドが行う。"
)

doc.add_heading("③ run_in_wsl() — COLMAP本体の呼び出し", level=2)
add_note("ここから先はCOLMAP(WSL上のCUDA対応ビルド)の担当。")
doc.add_paragraph(
    "subprocess.run([\"wsl\", \"--\"] + args) で、WSL2内にビルド済みの colmap コマンドを"
    "そのまま実行する。渡している引数は次の通り。"
)
add_code_block(
    "colmap automatic_reconstructor\n"
    "  --workspace_path <workspace>       # 作業フォルダ\n"
    "  --image_path <workspace>/images     # ①で作った画像フォルダ\n"
    "  --data_type video                   # 連番フレーム向けにsequential matcherを使う\n"
    "  --quality <quality>                  # low/medium/high/extreme\n"
    "  --single_camera 1                    # 同一カメラなので内部パラメータを共有\n"
    "  --sparse 1 --dense <0 or 1>          # スパース/密点群の生成有無"
)
doc.add_paragraph(
    "automatic_reconstructor は内部で「特徴点抽出→マッチング→Incremental SfM(疎点群・姿勢推定)"
    "→(dense=1なら)image_undistorter→patch_match_stereo→stereo_fusion」までを"
    "一括で実行してくれる、COLMAPの“おまかせ”コマンドである。"
)

# ==========================================
# 2_ply_to_splat.py
# ==========================================
doc.add_heading("2_ply_to_splat.py", level=1)
doc.add_paragraph("役割: 3DGSが出力したPLYを、WebGLビューア用の軽量な.splat形式に変換する。")
add_note("これはCOLMAP/3DGSを呼ばない、完全にPython(numpy)だけの処理。")
doc.add_paragraph(
    "plyfileライブラリでPLYを読み込み、各ガウシアンの position・scale(exp変換)・"
    "color(球面調和関数の0次項から算出)・opacity(シグモイド変換)・rotation(クォータニオン正規化)を、"
    "1点あたり32バイトの固定長バイナリレコードに詰め直して書き出す。"
)
add_code_block(
    "position = [x, y, z]                       # float32 x3 = 12byte\n"
    "scales   = exp([scale_0, scale_1, scale_2]) # float32 x3 = 12byte\n"
    "color    = [r, g, b, opacity] を0-255に      # uint8  x4 =  4byte\n"
    "rot      = 正規化した quaternion を0-255に    # uint8  x4 =  4byte\n"
    "                                              合計 32byte/点"
)
doc.add_paragraph(
    "表示時に見た目の破綻を防ぐため、「大きくて不透明なガウシアン」を先に並べる"
    "ソートも行っている(WebGL側での描画順の都合)。"
)

# ==========================================
# 3_train_3dgs.py
# ==========================================
doc.add_heading("3_train_3dgs.py", level=1)
doc.add_paragraph("役割: WSL2上の3D Gaussian Splattingを学習させ、ガウシアン点群を生成する。")

doc.add_heading("① to_wsl_path() — 1_colmap_reconstruct.pyと同じ役割", level=2)
add_note("パス変換のみ。COLMAPスクリプトと同じ仕組みを再利用している。")

doc.add_heading("② 学習の呼び出し — 3D Gaussian Splattingの担当", level=2)
add_note("subprocess.run([\"wsl\", ...]) でWSL上のPython(gaussian-splatting用のvenv)を実行している。")
doc.add_paragraph(
    "COLMAPが作った歪み補正済みデータセット(images/ + sparse/0/*.bin)を"
    "そのまま3D Gaussian Splattingの学習データとして渡す。"
)
add_code_block(
    "~/gaussian-splatting/venv/bin/python train.py\n"
    "  -s <colmap_workspace>/dense   # COLMAPが作った歪み補正済みデータセット\n"
    "  -m <model_output_dir>          # 学習結果の出力先\n"
    "  --iterations 30000\n"
    "  --eval"
)
doc.add_paragraph(
    "train.py 自体はPythonスクリプトだが、これは我々のスクリプトではなく "
    "graphdeco-inria/gaussian-splatting 公式リポジトリのコードである。"
    "PyTorch + CUDA上でガウシアンのパラメータ(位置・スケール・回転・不透明度・球面調和関数)を"
    "最適化し、一定イテレーションごとに point_cloud/iteration_N/point_cloud.ply として保存する。"
)

# ==========================================
# 補助スクリプト
# ==========================================
doc.add_heading("補助スクリプト(ドキュメント作成用)", level=1)
doc.add_paragraph(
    "以下はパイプライン本体には関係なく、このガイド/Qiita記事用の画像を作るためだけのスクリプト。"
)
for name, desc in [
    ("render_previews.py", "Open3Dでスパース点群をオフスクリーンレンダリングし、PNG画像として保存する。"),
    ("crop_preview.py", "レンダリング画像の余白をピクセル値から自動検出してクロップする(PIL/numpyのみ)。"),
    ("make_pipeline_diagram.py", "matplotlibでパイプライン全体図(フローチャート)を描画する。"),
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(name)
    run.bold = True
    p.add_run(f" — {desc}")

# ==========================================
# まとめ図
# ==========================================
doc.add_heading("Python と COLMAP/3DGS の役割分担まとめ", level=1)
summary_table = doc.add_table(rows=1, cols=2)
summary_table.style = "Light Grid Accent 1"
hdr = summary_table.rows[0].cells
hdr[0].text = "Pythonが担当する部分"
hdr[1].text = "COLMAP / 3DGS(外部コマンド)が担当する部分"
row = summary_table.add_row().cells
row[0].text = (
    "・動画からのフレーム抽出(OpenCV)\n"
    "・WindowsパスとWSLパスの相互変換\n"
    "・subprocessによる外部コマンド呼び出しと結果確認\n"
    "・PLY→.splat形式への変換(numpy)"
)
row[1].text = (
    "・特徴点抽出/マッチング、SfM、画像の歪み補正、\n"
    "  密なステレオ復元(すべてCOLMAP)\n"
    "・ガウシアンスプラットの学習そのもの\n"
    "  (3D Gaussian Splatting公式のtrain.py、PyTorch+CUDA)"
)

doc.save("../script_explanation.docx")
print("saved script_explanation.docx")
