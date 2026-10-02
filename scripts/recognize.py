"""recognize.py — face(YuNet DNN) | qr | diff：--image <路径> 或 --latest 取缓存最新帧；diff 须 --a --b。
契约 v2（视觉描述契约）为可选超集：--structured 或 --preprocess gray,edge 时启用，默认关闭＝旧输出零回归。
红线：灰度≠深度——前后关系只用遮挡轮廓+基线 y（地面假设）+相对大小融合；emotion/affect 仅 face 任务且标 domain。
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera_common as cc
import fetch_model
import vision_v2 as v2


def latest():
    d = cc.capdir(); fs = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")]
    if not fs: raise SystemExit("缓存无图像，先运行 camera.py snap")
    return max(fs, key=os.path.getmtime)


def face(cv2, img):
    m = fetch_model.path()
    if not os.path.isfile(m):
        raise SystemExit("缺 YuNet 模型：经用户确认后运行 python scripts/fetch_model.py --yes"
                         "（OpenCV5 已移除 Haar CascadeClassifier）")
    fd = cv2.FaceDetectorYN_create(m, "", (img.shape[1], img.shape[0]), 0.6, 0.3, 5000)
    _, rs = fd.detect(img)
    rows = list(rs) if rs is not None else []
    r = {"schema": "detection", "task": "face", "count": len(rows),
         "boxes": [[int(x) for x in row[:4]] for row in rows]}
    r["_scores"] = [float(row[14]) for row in rows if len(row) > 14]
    return r


def qr(cv2, img):
    data, pts, _ = cv2.QRCodeDetector().detectAndDecode(img)
    r = {"schema": "detection", "task": "qr", "count": int(bool(data)), "text": data or None}
    r["_pts"] = None if pts is None or not len(pts) else pts.reshape(-1, 2).tolist()
    return r


def diff(cv2, a, b):
    ia, ib = cv2.imread(a), cv2.imread(b)
    if ia is None or ib is None: raise SystemExit("读图失败: %s / %s" % (a, b))
    gray = lambda x: cv2.GaussianBlur(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (21, 21), 0)
    _, th = cv2.threshold(cv2.absdiff(gray(ia), gray(ib)), 25, 255, cv2.THRESH_BINARY)
    ratio = float((th > 0).mean())
    r = {"schema": "detection", "task": "diff", "count": int(ratio > 0.05),
         "changed_ratio": round(ratio, 4)}
    r["_imgs"] = (ia, ib)
    return r


def strip_internal(r):
    """输出前剔除内部键（下划线前缀）——保证默认旧契约字段一字不差。"""
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _norm(box, W, H):
    return [round(box[0] / W, 4), round(box[1] / H, 4),
            round(box[2] / W, 4), round(box[3] / H, 4)]


def _quad(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))]


def _objs(r, W, H):
    """旧 boxes / qr 角点升为契约 v2 objects[]（旧字段不删不改名）。"""
    objs = []
    if r["task"] == "face":
        sc = r.get("_scores") or []
        for i, box in enumerate(r["boxes"]):
            objs.append({"id": i + 1, "type": "face", "label": "face",
                         "confidence": round(sc[i], 4) if i < len(sc) else None,
                         "bbox_px": list(box), "bbox_norm": _norm(box, W, H),
                         "center_px": [box[0] + box[2] // 2, box[1] + box[3] // 2]})
    elif r["task"] == "qr" and r.get("_pts"):
        box = _quad(r["_pts"])
        objs.append({"id": 1, "type": "qr", "label": "qr", "confidence": None,
                     "bbox_px": box, "bbox_norm": _norm(box, W, H),
                     "center_px": [box[0] + box[2] // 2, box[1] + box[3] // 2]})
    for o in objs:
        o["actionable"] = False
        o["action_hint"] = "none"
    return objs



def _clamp(o, W, H):
    """框裁进画面：bbox_px / bbox_norm / center_px 三者始终一致。"""
    x, y, w, h = o["bbox_px"]
    x, y = max(0, min(W - 2, x)), max(0, min(H - 2, y))
    w, h = max(1, min(w, W - x)), max(1, min(h, H - y))
    o["bbox_px"] = [x, y, w, h]
    o["bbox_norm"] = _norm([x, y, w, h], W, H)
    o["center_px"] = [x + w // 2, y + h // 2]
    return o

def _affect(task, via_gateway):
    """情绪限定域：仅 face 输出且标 domain；无模型＝null，绝不硬猜。"""
    if via_gateway:
        raise SystemExit("--via-gateway 未接线：本技能无网关情绪模型，拒绝硬猜"
                         "（契约 §0-2 / 红线 4）")
    if task != "face":
        return None, None
    affect = {"valence": None, "arousal": None, "domain": "face",
              "model": None, "note": "无情绪模型：emotion 置 null，不做网关硬猜"}
    return None, affect


def apply_v2(cv2, img, r, path, preprocess, edge_mode, via_gateway):
    """契约 v2 超集：只增字段，旧字段原样保留。"""
    H, W = img.shape[:2]
    ch, _g, edge = v2.channels(cv2, img, preprocess, edge_mode)
    r.update({"schema_version": 2, "channels": ch,
              "source": {"kind": "camera", "window": os.path.basename(path),
                         "image": os.path.abspath(path), "size_px": [W, H],
                         "dpi_scale": 1.0, "monitor": None}})
    objs = _objs(r, W, H)
    objs = [_clamp(o, W, H) for o in objs]
    for o in objs:
        x, y, w, h = o["bbox_px"]
        w, h = max(1, min(w, W - x)), max(1, min(h, H - y))
        o["bbox_px"] = [x, y, w, h]
        o["bbox_norm"] = _norm([x, y, w, h], W, H)
        o["center_px"] = [x + w // 2, y + h // 2]
        o["channel"] = v2.object_channel(cv2, img, o["bbox_px"])
        o["emotion"], o["affect"] = _affect(r["task"], via_gateway)
    pairs, z, cues = [], {}, {}
    if len(objs) >= 2:
        ps, score, occ, meta = v2.relations(cv2, img, edge, objs)
        pairs = ps
        z = v2.z_orders(objs, score)
        amax = float(max(m["area"] for m in meta))
        smax = max(m["sharp"] for m in meta)
        cues = v2.depth_cues(meta, occ, amax, smax)
    elif len(objs) == 1:
        z = {objs[0]["id"]: 0}
    for o in objs:
        o["z_order"] = z.get(o["id"], 0)
        o["z_basis"] = "pixel_occlusion"
        if o["id"] in cues:
            o["depth_cues"] = cues[o["id"]]
    r["objects"] = objs
    r["relations"] = {"pairs": pairs, "note": v2.NOTE}
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["face", "qr", "diff"])
    ap.add_argument("--image"); ap.add_argument("--a"); ap.add_argument("--b")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--structured", action="store_true", help="契约 v2 超集（默认关＝旧输出）")
    ap.add_argument("--preprocess", default="", help="逗号分隔 gray,edge；给了即启用 v2")
    ap.add_argument("--edge-mode", choices=["canny", "sobel"], default="canny")
    ap.add_argument("--via-gateway", action="store_true",
                    help="显式允许网关情绪推断（本技能未接线则报错，不硬猜）")
    x = ap.parse_args(); cv2 = cc.cv2()
    pre = [s.strip() for s in x.preprocess.split(",") if s.strip()]
    bad = [s for s in pre if s not in ("gray", "edge")]
    if bad:
        raise SystemExit("--preprocess 仅支持 gray|edge，未知: %s" % ",".join(bad))
    if x.via_gateway:
        raise SystemExit("--via-gateway 未接线：本技能无网关情绪模型，拒绝硬猜"
                         "（契约 §0-2 / 红线 4）；face 任务 emotion 保持 null")
    v2on = bool(x.structured or pre)
    modes = pre or ["gray", "edge"]
    if x.task == "diff":
        pa = x.a or (latest() if x.latest else None)
        if not pa or not x.b:
            raise SystemExit("diff 须 --a --b 两图（--a 可用 --latest 代）")
        r = diff(cv2, pa, x.b)
        r["a"] = os.path.basename(pa); r["b"] = os.path.basename(x.b)
        if v2on:
            ia, ib = r["_imgs"]
            r = apply_v2(cv2, ia, r, pa, modes, x.edge_mode, x.via_gateway)
            cb, _g, _e = v2.channels(cv2, ib, modes, x.edge_mode)
            r["channels_b"] = cb
    else:
        p = x.image or (latest() if x.latest else None)
        if not p:
            raise SystemExit("须指定 --image 或 --latest")
        img = cv2.imread(p)
        if img is None:
            raise SystemExit("读图失败: " + p)
        r = face(cv2, img) if x.task == "face" else qr(cv2, img)
        r["image"] = os.path.basename(p)
        if v2on:
            r = apply_v2(cv2, img, r, p, modes, x.edge_mode, x.via_gateway)
    r = strip_internal(r)
    cc.notify("recognize", "%s count=%s%s" % (x.task, r["count"],
                                              " v2" if v2on else ""))
    cc.jout(r)
