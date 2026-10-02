"""vision_v2.py — 契约 v2 扩展：通道统计 / 灰度+边缘预处理 / 前后关系。
前后关系只用「遮挡轮廓压越 + 基线 y（地面假设）+ 相对大小」融合判定。
红线：灰度≠深度——禁止把「暗=远、亮=近」当规律，灰度只用于降噪与边缘/遮挡边界。
"""
import os
import numpy as np

BINS = 8
NOTE = ("灰度不代表深度；z 由遮挡轮廓+基线y(地面假设)+相对大小融合，"
        "框为外接矩形代理，仅供排序参考")
WEIGHT = {"occlusion": 0.5, "baseline_y": 0.3, "relative_size": 0.2}


def edge_map(cv2, img, mode="canny"):
    """灰度 + 边缘图（遮挡边界用）；mode=canny|sobel。"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    if mode == "sobel":
        # OpenCV 5 实测：Sobel 不接受 CV_16F，须 CV_32F/CV_64F
        sx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        return g, cv2.convertScaleAbs(cv2.magnitude(sx, sy))
    return g, cv2.Canny(g, 60, 180)


def channels(cv2, img, preprocess, edge_mode="canny"):
    """顶层 channels 块（契约 v2 §1）：均值/饱和/对比/8 分箱/边缘密度。"""
    h, w = img.shape[:2]
    n = max(1, h * w)
    g, e = edge_map(cv2, img, edge_mode)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([g], [0], None, [BINS], [0, 256]).ravel()
    ch = {"mode": "rgb", "preprocess": list(preprocess),
          "mean_rgb": [round(float(img[:, :, c].mean()), 2) for c in range(3)],
          "saturation": round(float(hsv[:, :, 1].mean()) / 255.0, 4),
          "contrast": round(float(g.std()), 2),
          "gray_mean": round(float(g.mean()), 2),
          "edge_density": round(float((e > 0).mean()), 4),
          "gray_hist_8": [round(float(v) / n, 4) for v in hist]}
    return ch, g, e


def object_channel(cv2, img, box):
    """单对象裁剪区的 channel 块。"""
    x, y, w, h = [int(v) for v in box]
    x, y = max(0, x), max(0, y)
    crop = img[y:min(img.shape[0], y + max(1, h)), x:min(img.shape[1], x + max(1, w))]
    if crop.size == 0:
        return {"mean_rgb": [0.0, 0.0, 0.0], "saturation": 0.0, "gray_mean": 0.0,
                "edge_density": 0.0, "alpha": 1.0}
    g, e = edge_map(cv2, crop)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return {"mean_rgb": [round(float(crop[:, :, c].mean()), 2) for c in range(3)],
            "saturation": round(float(hsv[:, :, 1].mean()) / 255.0, 4),
            "gray_mean": round(float(g.mean()), 2),
            "edge_density": round(float((e > 0).mean()), 4), "alpha": 1.0}


def _perim_mask(shape, box):
    """框四边掩膜（以边界为中心 ±2px，容 Canny 边缘定位偏移一像素）。"""
    x, y, w, h = [int(v) for v in box]
    m = np.zeros(shape[:2], dtype=bool)
    m[y:y + h, max(0, x - 2):x + 3] = True
    m[y:y + h, max(0, x + w - 2):x + w + 3] = True
    m[max(0, y - 2):y + 3, x:x + w] = True
    m[max(0, y + h - 2):y + h + 3, x:x + w] = True
    return m


def _solid(shape, box):
    x, y, w, h = [int(v) for v in box]
    m = np.zeros(shape[:2], dtype=bool)
    m[y:y + h, x:x + w] = True
    return m


def _survival(edge, box, other):
    """轮廓存活率：本框轮廓落在 other 范围内的那一段，仍有边缘像素的比例。

    压在上方的物体其轮廓在对方区域内依然可见（值高）；被遮挡者的轮廓被抹去（值≈0）。
    无可比段（无交叠/完全包含）返回 None，此时不出遮挡票，避免假判定。
    """
    sel = _perim_mask(edge.shape, box) & _solid(edge.shape, other)
    if not sel.any():
        return None
    return round(float((edge[sel] > 0).mean()), 4)


def _inter(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1 - x0, y1 - y0)


def relations(cv2, img, edge, objs, min_overlap=0.02):
    """前后关系融合判定：遮挡轮廓 + 基线 y（地面假设）+ 相对大小。
    返回 (pairs, z_order, depth_cues)；灰度/亮度一律不参与深度推断。"""
    H = img.shape[0]
    meta = []
    for o in objs:
        box = [int(v) for v in o["bbox_px"]]
        sub = img[box[1]:box[1] + box[3], box[0]:box[0] + box[2]]
        sharp = 0.0
        if sub.size:
            sharp = float(cv2.Laplacian(cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY),
                                        cv2.CV_64F).var())
        meta.append({"id": o["id"], "type": o.get("type", "other"), "box": box,
                     "area": max(1, box[2] * box[3]),
                     "base": round((box[1] + box[3]) / float(H), 4), "sharp": sharp})
    areas = [m["area"] for m in meta] or [1]
    amax = float(max(areas))
    pairs = []
    score = {m["id"]: 0.0 for m in meta}
    occ = {m["id"]: {"occludes": [], "occluded_by": []} for m in meta}
    for i in range(len(meta)):
        for j in range(i + 1, len(meta)):
            a, b = meta[i], meta[j]
            rect = _inter(a["box"], b["box"])
            if not rect:
                continue
            if rect[2] * rect[3] / min(a["area"], b["area"]) < min_overlap:
                continue
            votes = _votes(edge, a, b, amax)
            if not votes:
                continue
            tally = {}
            for cue, win in votes.items():
                tally[win] = tally.get(win, 0.0) + WEIGHT[cue]
            vals = sorted(tally.values(), reverse=True)
            if len(vals) > 1 and abs(vals[0] - vals[1]) < 1e-9:
                continue  # 线索完全打平：不给结论，宁缺毋滥
            front = max(tally, key=tally.get)
            conf = round(min(0.95, (tally[front] / sum(tally.values()))
                                   * (0.4 + 0.2 * len(votes))), 3)
            back = b["id"] if front == a["id"] else a["id"]
            score[front] += conf
            score[back] -= conf
            occ[front]["occludes"].append(back)
            occ[back]["occluded_by"].append(front)
            pairs.append({"a": a["id"], "b": b["id"], "in_front": front == a["id"],
                          "cues": sorted(votes), "confidence": conf})
    return pairs, score, occ, meta


def _votes(edge, a, b, amax):
    """三线索投票：遮挡轮廓存活率 / 基线 y（地面假设）/ 同类相对大小。"""
    v = {}
    sa, sb = _survival(edge, a["box"], b["box"]), _survival(edge, b["box"], a["box"])
    if sa is not None and sb is not None and abs(sa - sb) > 0.05:
        v["occlusion"] = a["id"] if sa > sb else b["id"]
    if abs(a["base"] - b["base"]) > 0.01:
        v["baseline_y"] = a["id"] if a["base"] > b["base"] else b["id"]
    if a["type"] == b["type"] and abs(a["area"] - b["area"]) / amax > 0.05:
        v["relative_size"] = a["id"] if a["area"] > b["area"] else b["id"]
    return v


def z_orders(objs, score):
    """z_order：0＝最前（离镜头最近/遮挡他者），递增向后；口径同 window_z。"""
    order = sorted(objs, key=lambda o: -score.get(o["id"], 0.0))
    return {o["id"]: k for k, o in enumerate(order)}


def depth_cues(meta, occ, amax, smax):
    """逐对象深度线索（relative_size / baseline_y_norm / blur 代理）。"""
    out = {}
    for m in meta:
        blur = 0.0 if smax <= 0 else round(max(0.0, 1.0 - m["sharp"] / smax), 4)
        out[m["id"]] = {"occludes": occ[m["id"]]["occludes"],
                        "occluded_by": occ[m["id"]]["occluded_by"],
                        "relative_size": round(m["area"] / amax, 4),
                        "baseline_y_norm": m["base"], "blur": blur}
    return out
