"""Qiita投稿用のWord原稿(.docx)を作成する。"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

IMG = "../images"

doc = Document()

# 既定フォントを日本語対応に
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
    p_format = p.paragraph_format
    return p


def add_image(path, width_cm=15, caption=None):
    doc.add_picture(path, width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        cap = doc.add_paragraph(caption)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].font.size = Pt(9)
        cap.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)


# ==========================================
# タイトル
# ==========================================
title = doc.add_heading("スマホ動画から3D Gaussian Splattingでモデルを作ってみた(COLMAP + WSL2 + CUDA)", level=0)

lead = doc.add_paragraph(
    "iPhoneで撮った1本の動画から、COLMAPとWSL2、そして3D Gaussian Splatting(3DGS)を使って"
    "3Dモデル(ガウシアンスプラット)を作成するまでの記録です。"
    "Windows上でCOLMAPの実行ファイルが謎に無言で落ちる、新しいGPU(RTX 50シリーズ)特有のCUDAバグ、"
    "WSLgでウィンドウが表示されない問題など、想定以上にハマりどころが多かったので、"
    "同じことをやろうとしている人の参考になればと思い書きます。"
)

# ==========================================
# はじめに
# ==========================================
doc.add_heading("この記事でやること", level=1)
doc.add_paragraph(
    "スマートフォンで対象物の周りをぐるっと撮影した動画1本から、次の手順で3Dガウシアンスプラットを作ります。"
)
for i, s in enumerate([
    "動画からフレームを抽出する",
    "COLMAPでカメラの位置・向きとスパースな3D点群を推定する(Structure from Motion)",
    "COLMAPで画像の歪みを補正する(3DGS学習の前処理)",
    "3D Gaussian Splattingで学習する",
    "ブラウザ(WebGL)で結果を確認する",
], 1):
    doc.add_paragraph(f"{i}. {s}", style="List Number")

add_image(f"{IMG}/pipeline_overview.png", width_cm=16, caption="全体のパイプライン")

# ==========================================
# 環境
# ==========================================
doc.add_heading("実行環境", level=1)
doc.add_paragraph(
    "Windows 11 + WSL2(Ubuntu)という構成です。COLMAPと3D Gaussian SplattingはどちらもWSL2上に"
    "CUDA対応でビルドしています。理由は後述しますが、Windowsネイティブ版のCOLMAPが"
    "このマシンでは実行できなかったためです。"
)
doc.add_paragraph("・GPU: NVIDIA GeForce RTX 5060(8GB)")
doc.add_paragraph("・WSL2: Ubuntu、CUDA Toolkit 13.2")
doc.add_paragraph("・COLMAP: 4.2.0(ソースからCUDA有効でビルド)")
doc.add_paragraph("・3D Gaussian Splatting: graphdeco-inria公式実装、PyTorch 2.14 + CUDA 13.2")

# ==========================================
# Step 1
# ==========================================
doc.add_heading("Step 1: 動画からフレーム抽出 → COLMAPでカメラ姿勢・スパース点群を推定", level=1)
doc.add_paragraph(
    "COLMAPは画像ファイルの集まりを処理するツールで、動画ファイルは直接読み込めません。"
    "そのため、まずPython(OpenCV)側で動画から一定間隔でフレームを抜き出し、静止画として保存します。"
    "今回は約320フレームの動画から5フレームおきに抜き出し、64枚の静止画にしました。"
)
add_code_block(
    "import cv2\n\n"
    "def extract_frames(video_path, images_dir, frame_step):\n"
    "    cap = cv2.VideoCapture(video_path)\n"
    "    idx, saved = 0, 0\n"
    "    ok, frame = cap.read()\n"
    "    while ok:\n"
    "        if idx % frame_step == 0:\n"
    "            cv2.imwrite(f\"{images_dir}/frame_{idx:05d}.jpg\", frame)\n"
    "            saved += 1\n"
    "        ok, frame = cap.read()\n"
    "        idx += 1\n"
    "    cap.release()\n"
    "    return saved"
)
add_image(f"{IMG}/00_sample_frame.jpg", width_cm=12, caption="Pythonで動画から抽出したフレームの例")

doc.add_paragraph(
    "静止画が用意できたら、ここから先はCOLMAP(Python側からsubprocessで呼び出し)の出番です。"
    "COLMAPの automatic_reconstructor に画像フォルダを渡すと、内部でSIFTによる特徴点抽出・"
    "マッチングを行い、Incremental SfM でカメラの位置・向きと、対応点から三角測量した"
    "スパースな3D点群を同時に推定します。"
)
add_image(f"{IMG}/01_sift_matching.jpg", width_cm=16, caption="隣接フレーム間のSIFT特徴点マッチング")

doc.add_paragraph("64枚全てのカメラ姿勢の推定に成功し、42,554点のスパース点群が得られました。")
add_image(f"{IMG}/03_sparse_pointcloud.png", width_cm=12, caption="推定されたスパース点群(Open3Dでレンダリング)")

doc.add_paragraph("実行コマンドの例です(automatic_reconstructorはCPUのみでも動作します):")
add_code_block(
    "colmap automatic_reconstructor \\\n"
    "  --workspace_path colmap_workspace \\\n"
    "  --image_path colmap_workspace/images \\\n"
    "  --data_type video \\\n"
    "  --quality high \\\n"
    "  --single_camera 1 \\\n"
    "  --sparse 1 --dense 1"
)
doc.add_paragraph(
    "3D Gaussian Splattingの学習には歪み補正済みの画像とカメラパラメータが必要なので、"
    "続けて image_undistorter を実行しておきます。"
)

# ==========================================
# Step 2
# ==========================================
doc.add_heading("Step 2(任意): 密なステレオ復元(MVS)", level=1)
doc.add_paragraph(
    "3DGSの学習自体にはスパース点群があれば十分ですが、CUDA対応でビルドしたCOLMAPなら"
    "patch_match_stereo → stereo_fusion で密な点群(この時は約162万点)も作れます。"
    "せっかくCUDAビルドを頑張ったので試してみました。"
)
add_image(f"{IMG}/02_disparity_map.jpg", width_cm=13, caption="ステレオマッチングによる視差マップの例")

# ==========================================
# Step 3
# ==========================================
doc.add_heading("Step 3: 3D Gaussian Splattingで学習", level=1)
doc.add_paragraph(
    "いよいよ本題の3D Gaussian Splattingです。graphdeco-inria公式実装の train.py に、"
    "Step 1で作った歪み補正済みデータセットを渡して学習します。"
)
add_code_block(
    "python train.py \\\n"
    "  -s colmap_workspace/dense \\\n"
    "  -m gaussian_splat_output \\\n"
    "  --iterations 30000 --eval"
)
doc.add_paragraph(
    "42,554点のスパース点群から出発し、密度化(densification)を繰り返しながら学習が進みます。"
    "手元の環境(RTX 5060、8GB VRAM)では30,000イテレーションの学習に約1時間35分かかりました。"
    "最終的な結果は次の通りです。"
)
doc.add_paragraph("・生成されたガウシアン数: 690,781個", style="List Bullet")
doc.add_paragraph("・再投影誤差(PSNR): train 35.7 / test 30.1", style="List Bullet")

# ==========================================
# Step 4
# ==========================================
doc.add_heading("Step 4: 結果をブラウザで確認する", level=1)
doc.add_paragraph(
    "3DGSが出力するPLYファイルは、各点が位置だけでなくスケール・回転(クォータニオン)・不透明度・"
    "球面調和関数(view-dependentな色)を持つ特殊な形式です。そのため Open3D などの通常の"
    "点群ビューアで開いても正しく表示されません。"
)
doc.add_paragraph(
    "今回は antimatter15/splat というWebGLベースの軽量ビューアを使いました。"
    "PLYを32バイト/点の軽量な .splat 形式に変換し、ローカルサーバー経由でブラウザから開きます"
    "(file://で直接開くとfetchがCORSでブロックされるため、簡易HTTPサーバーを立てるのがポイントです)。"
)
add_code_block(
    "# PLY -> .splat 変換\n"
    "python ply_to_splat.py point_cloud.ply model.splat\n\n"
    "# ローカルサーバーを起動してブラウザで開く\n"
    "python -m http.server 8080\n"
    "# http://localhost:8080/ にアクセス"
)
doc.add_paragraph(
    "マウスドラッグで視点回転、スクロールで周回移動、右ドラッグ(またはCtrl/Cmd+ドラッグ)で"
    "前後移動ができ、690,781個のガウシアンスプラットがブラウザ上でぬるぬる動く様子を確認できました。"
)

# ==========================================
# つまずいたポイント
# ==========================================
doc.add_heading("つまずいたポイント集", level=1)
doc.add_paragraph(
    "ここまでたどり着くまでに、実際にハマったポイントを紹介します。"
    "同じ構成(新しめのNVIDIA GPU + WSL2)で試す人の参考になれば幸いです。"
)

table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
hdr[0].text = "症状"
hdr[1].text = "原因"
hdr[2].text = "対処"

rows = [
    (
        "Windows版COLMAPが起動直後、何も表示せず即終了する",
        "Windowsの「スマートアプリコントロール」が、未署名のDLL(gmp-10.dll等)の読み込みを"
        "ブロックしていた(イベントログのCode Integrityログで発覚)",
        "WSL2(Ubuntu)上にLinux版COLMAPをインストールする方針に変更",
    ),
    (
        "COLMAPのCUDA有効ビルドでnvccが謎のコンパイルエラー",
        "RTX 50シリーズ(Blackwell)向けにnvccのコンパイラバグが存在する",
        "CMAKE_CUDA_ARCHITECTURESをPTXのみ(90-virtual)にすることでJITコンパイルさせて回避",
    ),
    (
        "patch_match_stereoが“unsupported toolchain”で異常終了",
        "インストールしたCUDA Toolkit(13.3)がGPUドライバの対応上限(13.2)より新しかった",
        "ドライバに合わせてCUDA Toolkit 13.2を追加インストールし、そちらでビルドし直す",
    ),
    (
        "SIBRビューア等のビルドでboost_systemが見つからない",
        "Boost 1.90でboost_systemが完全ヘッダオンリー化され、コンパイル済みライブラリ自体が廃止された",
        "cmakeの依存コンポーネント一覧からsystemを除外する",
    ),
    (
        "embree3/rtcore.hが見つからない",
        "新しいUbuntuにはembree4しか存在せず、依存コード側はembree3のAPI(RTCIntersectContext等)を前提としていた",
        "ヘッダ・ライブラリにシンボリックリンクを張った上で、廃止APIを新APIに移植",
    ),
    (
        "3DGSビューア(SIBR_gaussianViewer_app)のウィンドウがWindowsデスクトップに出ない",
        "GLFWがWSLgのネイティブWaylandモードでウィンドウを作成しており、WSLg側の転送機構がそれを認識していなかった",
        "glfwInitHintでX11強制も試したが解決せず、最終的にWebGLビューア(ブラウザ)へ方針転換",
    ),
]
for r in rows:
    cells = table.add_row().cells
    for c, text in zip(cells, r):
        c.text = text

doc.add_paragraph()
doc.add_paragraph(
    "個人的に一番の学びは、「GUIアプリの表示問題を延々デバッグするより、"
    "ブラウザで完結する軽量なWebGLビューアに逃げた方が早い」ということでした。"
    "WSLgは便利ですが、ネイティブGUIアプリの表示周りはまだ癖が強い印象です。"
)

# ==========================================
# まとめ
# ==========================================
doc.add_heading("まとめ", level=1)
doc.add_paragraph(
    "スマホで撮った動画1本から、COLMAP(SfM/MVS)と3D Gaussian Splattingを組み合わせて"
    "3Dガウシアンスプラットを作成できました。環境構築(特に最新GPU × WSL2 × CUDAの組み合わせ)は"
    "トラブルが多かったですが、パイプライン自体は一度動いてしまえば非常に手軽で、"
    "身近な物や場所を手早く3Dスキャンして遊べるのが魅力的だと感じました。"
)

doc.add_heading("参考リンク", level=1)
for link in [
    "COLMAP: https://colmap.github.io/",
    "3D Gaussian Splatting(公式実装): https://github.com/graphdeco-inria/gaussian-splatting",
    "WebGLビューア: https://github.com/antimatter15/splat",
]:
    doc.add_paragraph(link, style="List Bullet")

doc.save("../qiita_draft.docx")
print("saved qiita_draft.docx")
