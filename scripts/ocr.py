"""ocr.py — 图中文字识别：仅用已装后端（paddleocr→easyocr→pytesseract 顺序探测），不自动装依赖。
--preprocess gray 为契约 v2 可选预处理（灰度+自适应阈值，提升召回）；默认关闭＝旧行为零回归。
预处理产物只写平台缓存目录（inside_cache 兜底），绝不写技能目录；敏感串只报类别不复述原文。
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera_common as cc
from recognize import latest


def _paddle(path):
    from paddleocr import PaddleOCR
    res = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False).ocr(path)
    return [l[1][0] for pg in res or [] for l in pg]


def _easy(path):
    import easyocr
    return [t.strip() for t in easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
            .readtext(path, detail=0)]


def _tess(path):
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").splitlines()


BACKENDS = {"paddleocr": ("paddleocr", _paddle), "easyocr": ("easyocr", _easy),
            "pytesseract": ("pytesseract", _tess)}


def preprocess_gray(path):
    """灰度 + 自适应二值化；产物落缓存目录，不覆盖原帧。"""
    cv2 = cc.cv2()
    img = cv2.imread(path)
    if img is None:
        raise SystemExit("读图失败: " + path)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 10)
    stem = os.path.basename(path).rsplit(".", 1)[0]
    out = os.path.join(cc.capdir(), "ocr_pre_%s.png" % stem)
    if not cc.inside_cache(out):
        raise SystemExit("预处理产物越出缓存目录，拒写: " + out)
    if not cv2.imwrite(out, th):
        raise SystemExit("预处理产物写入失败: " + out)
    return out


def pick_backend(want):
    """先探测已装后端，一个都没有就立即报错——不先写预处理产物。"""
    for name in ([want] if want else list(BACKENDS)):
        try:
            __import__(BACKENDS[name][0])
            return name
        except ImportError:
            continue
    raise SystemExit("未装 OCR 后端：经用户确认装三选一 paddleocr|easyocr|pytesseract"
                     "（后者还需系统 tesseract 程序）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image"); ap.add_argument("--latest", action="store_true")
    ap.add_argument("--backend", choices=list(BACKENDS))
    ap.add_argument("--preprocess", default="", help="逗号分隔，目前仅 gray（灰度+自适应阈值）")
    x = ap.parse_args()
    pre = [s.strip() for s in x.preprocess.split(",") if s.strip()]
    bad = [s for s in pre if s != "gray"]
    if bad:
        raise SystemExit("--preprocess 仅支持 gray，未知: %s" % ",".join(bad))
    src = x.image or (latest() if x.latest else None)
    if not src:
        raise SystemExit("须指定 --image 或 --latest")
    name = pick_backend(x.backend)
    p = preprocess_gray(src) if pre else src
    cc.notify("ocr", "%s via %s%s" % (os.path.basename(p), name,
                                      " pre=" + ",".join(pre) if pre else ""))
    try:
        lines = [l for l in BACKENDS[name][1](p) if l and str(l).strip()]
    except Exception as e:
        raise SystemExit("后端 %s 失败: %s" % (name, e))
    r = {"schema": "detection", "task": "ocr", "backend": name,
         "count": len(lines), "lines": lines}
    if pre:
        r["schema_version"] = 2
        r["preprocess"] = pre
        r["source_image"] = os.path.basename(src)
        r["preprocessed_image"] = os.path.basename(p)
    cc.jout(r)
