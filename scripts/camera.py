"""camera.py — list | snap | frames | clean：图像仅落固定缓存，每帧附 NOTICE；连拍须显式 --n>=2。"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera_common as cc

def _enumerate(cv2):
    found = []
    for i in range(6):
        cap = cv2.VideoCapture(i)
        ok = cap.isOpened(); r, _ = cap.read() if ok else (False, None)
        if ok and r: found.append({"idx": i, "w": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "h": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})
        cap.release()
    return found

def _grab(cv2, cap, n, interval):
    files = []
    for k in range(n):
        ok, frame = cap.read()
        if not ok: break
        p = os.path.join(cc.capdir(), time.strftime("%Y%m%d-%H%M%S") + ("-c%02d.png" % k if n > 1 else ".png"))
        if not cv2.imwrite(p, frame): raise SystemExit("写图失败: " + p)
        files.append(p); cc.notify("capture", "saved " + os.path.basename(p))
        if k < n - 1: time.sleep(interval)
    return files

def _shot(cv2, a):
    if a.cmd == "frames" and a.n < 2: raise SystemExit("frames 须 --n>=2（单帧请用 snap）")
    cap = cv2.VideoCapture(a.idx)
    if not cap.isOpened(): raise SystemExit("无法打开摄像头 idx=%d（不存在/被占用/无权限）" % a.idx)
    if a.w: cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.w)
    if a.h: cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.h)
    try: files = _grab(cv2, cap, 1 if a.cmd == "snap" else a.n, a.interval)
    finally: cap.release()
    if not files: raise SystemExit("读帧失败，未写入任何占位文件")
    cc.jout({"saved": files, "notice": os.path.join(cc.home(), "NOTICE.md")})

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["list", "snap", "frames", "clean"])
    ap.add_argument("--idx", type=int, default=0); ap.add_argument("--w", type=int); ap.add_argument("--h", type=int)
    ap.add_argument("--n", type=int, default=1); ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--keep-days", type=int, default=7)
    a = ap.parse_args(); cv2 = cc.cv2()
    if a.cmd == "clean":
        d = cc.capdir(); cut = time.time() - a.keep_days * 86400
        rm = [f for f in os.listdir(d) if os.path.getmtime(os.path.join(d, f)) < cut]
        [os.remove(os.path.join(d, f)) for f in rm]; cc.jout({"removed": len(rm), "dir": d})
    elif a.cmd == "list":
        cc.notify("list", "枚举摄像头，未存图"); cc.jout({"cameras": _enumerate(cv2)})
    else:
        _shot(cv2, a)
