# camera-vision

摄像头调用及图像识别 Agent Skill：枚举/抓拍/连拍、人脸、二维码、运动检测、可选 OCR。独立于 safe-mouse-automation（无鼠标键盘操作，只管视觉）。

## 依赖

- 必装：`pip install opencv-python`（已测 5.0.0 / Python 3.14）
- 可选（OCR 三选一）：`paddleocr` | `easyocr` | `pytesseract`（后者另需系统 tesseract 程序）
- 本 skill 不会自动安装任何依赖。

## 快速开始

```bash
python scripts/camera.py list                      # 枚举可用摄像头
python scripts/camera.py snap --idx 0              # 单帧抓拍（写缓存+NOTICE）
python scripts/recognize.py face --latest          # 对最新帧做人脸检测
python scripts/recognize.py qr --image a.png       # 解二维码
python scripts/recognize.py diff --a a.png --b b.png   # 两帧运动比对
python scripts/ocr.py --latest                     # 最新帧文字识别
python scripts/recognize.py face --latest --structured --preprocess gray,edge  # 契约 v2 超集
python scripts/camera.py clean --keep-days 7       # 清理过期缓存
```

## 数据边界

图像与每笔使用告知存于 `%LOCALAPPDATA%\camera_vision\`（Windows；macOS/Linux 见 [camera_common.py](scripts/camera_common.py)），不进 skill 目录；`NOTICE.md` 逐笔记录何时开了哪个摄像头存了哪个文件。

## 结构

[SKILL.md](SKILL.md) 入口 · [scripts/](scripts/scripts.md) 脚本 · [schemas/](schemas/detection.schema.json) 契约（[v2 口径](schemas/vision_contract_v2_camera.md)） · [knowledge/](knowledge/knowledge.md) 知识库 · [resistance/](resistance/resistance.md) 红线与兜底 · [agent/](agent/CLAUDE.md) 四格式提示词
