"""fetch_model.py — 经用户确认后拉取 YuNet 人脸模型（face_detection_yunet_2023mar.onnx, ~230KB）到固定缓存。"""
import hashlib, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera_common as cc

URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"


def path():
    return os.path.join(cc.home(), "models", "face_detection_yunet_2023mar.onnx")


if __name__ == "__main__":
    if "--yes" not in sys.argv[1:]:
        raise SystemExit("下载模型须经用户确认：python scripts/fetch_model.py --yes（文件存 camera_vision/models/，不入库不写 skill 目录）")
    p = path()
    if os.path.isfile(p) and os.path.getsize(p) > 100000:
        cc.jout({"cached": p}); raise SystemExit(0)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        tmp = p + ".part"
        urllib.request.urlretrieve(URL, tmp)
        os.replace(tmp, p)
    except Exception as e:
        raise SystemExit("拉取失败: %s（检查网络或手动放置 %s）" % (e, p))
    if os.path.getsize(p) < 100000:
        os.remove(p); raise SystemExit("响应过小，疑似被门户劫持，已弃；请手动放置模型")
    cc.notify("fetch_model", "YuNet onnx 存入 models/")
    cc.jout({"saved": p, "sha1": hashlib.sha1(open(p, "rb").read()).hexdigest()[:12]})
