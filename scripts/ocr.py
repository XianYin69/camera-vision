"""ocr.py — 图中文字识别：仅用已装后端（paddleocr→easyocr→pytesseract 顺序探测），不自动装依赖。"""
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
    return [t.strip() for t in easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False).readtext(path, detail=0)]


def _tess(path):
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").splitlines()


BACKENDS = {"paddleocr": ("paddleocr", _paddle), "easyocr": ("easyocr", _easy), "pytesseract": ("pytesseract", _tess)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image"); ap.add_argument("--latest", action="store_true"); ap.add_argument("--backend", choices=list(BACKENDS))
    x = ap.parse_args(); p = x.image or (latest() if x.latest else None)
    if not p:
        raise SystemExit("须指定 --image 或 --latest")
    for name in ([x.backend] if x.backend else list(BACKENDS)):
        mod, fn = BACKENDS[name]
        try:
            __import__(mod)
        except ImportError:
            continue
        cc.notify("ocr", "%s via %s" % (os.path.basename(p), name))
        try:
            lines = [l for l in fn(p) if l and str(l).strip()]
        except Exception as e:
            raise SystemExit("后端 %s 失败: %s" % (name, e))
        cc.jout({"schema": "detection", "task": "ocr", "backend": name, "count": len(lines), "lines": lines})
        break
    else:
        raise SystemExit("未装 OCR 后端：经用户确认装三选一 paddleocr|easyocr|pytesseract（后者还需系统 tesseract 程序）")
