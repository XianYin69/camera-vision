"""camera_common.py — 固定缓存解析 / cv2 导入守卫 / 每笔使用 NOTICE 审计。缓存永不落 skill 目录。"""
import json, os, sys, time


def home():
    h = os.environ.get("CAMERA_VISION_HOME")
    if h:
        return h
    u = os.path.expanduser("~")
    if sys.platform == "win32":
        b = os.environ.get("LOCALAPPDATA") or u
    elif sys.platform == "darwin":
        b = os.path.join(u, "Library", "Caches")
    else:
        b = os.environ.get("XDG_CACHE_HOME") or os.path.join(u, ".cache")
    return os.path.join(b, "camera_vision")


def capdir():
    d = os.path.join(home(), "captures")
    os.makedirs(d, exist_ok=True)
    return d


def inside_cache(p):
    return os.path.abspath(p).startswith(os.path.abspath(home()) + os.sep)


def notify(op, detail):
    """每笔使用一条：时间/操作/对象写入 NOTICE.md，用户可随时查看与删除。"""
    p = os.path.join(home(), "NOTICE.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if new:
            f.write("# camera-vision 使用告知（NOTICE · 每笔一条 · 可随时查看/删除）\n\n")
        f.write("- %s %s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), op, detail))
    return p


def cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        raise SystemExit("缺依赖 opencv-python：经用户确认后执行 pip install opencv-python")


def jout(x):
    print(json.dumps(x, ensure_ascii=False, indent=2))
