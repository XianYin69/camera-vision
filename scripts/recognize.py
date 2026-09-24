"""recognize.py — face(YuNet DNN) | qr | diff：--image <路径> 或 --latest 取缓存最新帧；diff 须 --a --b。"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera_common as cc
import fetch_model

def latest():
    d = cc.capdir(); fs = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")]
    if not fs: raise SystemExit("缓存无图像，先运行 camera.py snap")
    return max(fs, key=os.path.getmtime)

def face(cv2, img):
    m = fetch_model.path()
    if not os.path.isfile(m):
        raise SystemExit("缺 YuNet 模型：经用户确认后运行 python scripts/fetch_model.py --yes（OpenCV5 已移除 Haar CascadeClassifier）")
    fd = cv2.FaceDetectorYN_create(m, "", (img.shape[1], img.shape[0]), 0.6, 0.3, 5000)
    _, rs = fd.detect(img)
    return {"schema": "detection", "task": "face", "count": int(0 if rs is None else len(rs)), "boxes": [[int(v) for v in r[:4]] for r in (rs if rs is not None else [])]}

def qr(cv2, img):
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return {"schema": "detection", "task": "qr", "count": int(bool(data)), "text": data or None}

def diff(cv2, a, b):
    ia, ib = cv2.imread(a), cv2.imread(b)
    if ia is None or ib is None: raise SystemExit("读图失败: %s / %s" % (a, b))
    gray = lambda x: cv2.GaussianBlur(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (21, 21), 0)
    _, th = cv2.threshold(cv2.absdiff(gray(ia), gray(ib)), 25, 255, cv2.THRESH_BINARY)
    ratio = float((th > 0).mean())
    return {"schema": "detection", "task": "diff", "count": int(ratio > 0.05), "changed_ratio": round(ratio, 4)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["face", "qr", "diff"])
    ap.add_argument("--image"); ap.add_argument("--a"); ap.add_argument("--b"); ap.add_argument("--latest", action="store_true")
    x = ap.parse_args(); cv2 = cc.cv2()
    if x.task == "diff":
        pa = x.a or (latest() if x.latest else None)
        if not pa or not x.b: raise SystemExit("diff 须 --a --b 两图（--a 可用 --latest 代）")
        r = diff(cv2, pa, x.b); r["a"] = os.path.basename(pa); r["b"] = os.path.basename(x.b)
    else:
        p = x.image or (latest() if x.latest else None)
        if not p: raise SystemExit("须指定 --image 或 --latest")
        img = cv2.imread(p)
        if img is None: raise SystemExit("读图失败: " + p)
        r = face(cv2, img) if x.task == "face" else qr(cv2, img)
        r["image"] = os.path.basename(p)
    cc.notify("recognize", "%s count=%s" % (x.task, r["count"]))
    cc.jout(r)
