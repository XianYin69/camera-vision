# scripts（脚本库）

本目录为 camera-vision 的可执行脚本：均英文小写下划线命名、不限行数（50 行红线仅限 markdown）、输出 JSON；缓存与审计只写固定缓存目录。

- [`camera_common.py`](camera_common.py)：解析固定缓存 `camera_vision/`（env `CAMERA_VISION_HOME` 覆盖；win=%LOCALAPPDATA% · mac=~/Library/Caches · linux=~/.cache）；`capdir()`、`inside_cache()` 写保护、`notify()` 每笔使用 NOTICE 审计、`cv2()` 导入守卫、`jout()`。
- [`camera.py`](camera.py)：`list` 枚举 idx0-5 · `snap --idx [--w --h]` 单帧 · `frames --n>=2 --interval` 连拍（须显式意图）· `clean --keep-days`；全部帧写缓存并逐帧记 NOTICE。
- [`recognize.py`](recognize.py)：`face`（YuNet DNN，需 fetch_model 拉取模型）· `qr`（QRCodeDetector）· `diff --a --b`（高斯模糊帧间差，占比>0.05 判动）；输入 `--image` 或 `--latest`。
- [`fetch_model.py`](fetch_model.py)：确认式拉取 YuNet onnx（须 `--yes`）到 `camera_vision/models/`；体积校验防门户劫持、记 sha1。
- [`ocr.py`](ocr.py)：按 paddleocr→easyocr→pytesseract 顺序探测已装后端；`--backend` 可指定；一个都没有则报错给安装建议，绝不自动装依赖。

输出契约见 [`../schemas/detection.schema.json`](../schemas/detection.schema.json)；依赖：opencv-python（必）、numpy（随附）、Pillow（仅 pytesseract 路径）。
