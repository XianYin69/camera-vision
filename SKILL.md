---
name: camera-vision
description: >
  摄像头调用及图像识别 skill（独立于 safe-mouse-automation）：枚举摄像头、单帧/显式批量抓拍、
  人脸（YuNet DNN，模型经确认拉取）、二维码、帧差运动检测与可选 OCR 后端（paddleocr/easyocr/pytesseract 三选一，绝不自动装依赖）；
  图像与审计只写平台缓存 camera_vision/ 目录，每次使用逐笔记 NOTICE.md，缺设备/依赖即明确报错不静默。
license: MIT
metadata:
  category: hardware
---

# camera-vision

使用 `camera-vision` skill 来完成用户请求。摄像头调用及图像识别：发现设备 → 受控采集 → 本地识别 → 结构化返回；不含鼠标键盘操作。

## 运行流程

1. **枚举**：`python scripts/camera.py list` 试开 idx0-5 并回读分辨率；用户指定或用唯一结果。
2. **采集**：`camera.py snap --idx N [--w --h]` 单帧；连拍须用户显式给张数 `frames --n>=2 --interval S`；帧只写固定缓存 `camera_vision/captures/` 并逐帧写 NOTICE。
3. **识别**：`recognize.py face|qr --latest|--image P`（face 首次需经用户确认 `fetch_model.py --yes` 拉 YuNet 模型）；两帧比对 `recognize.py diff --a A --b B`（占比>0.05 判变化）。契约 v2 超集须显式开关 `--structured` 或 `--preprocess gray,edge`（默认关＝旧输出零回归）。
4. **OCR**：`ocr.py [--backend X] [--preprocess gray]` 按 paddleocr→easyocr→pytesseract 探测已装者；一个未装 → 报三选一建议，经用户确认才安装。
5. **清理**：`camera.py clean --keep-days 7` 手动清缓存；无常驻进程。

## 依赖

`opencv-python`（必，已测 5.0.0/Python 3.14——其主命名空间已无 Haar `CascadeClassifier`，人脸走 YuNet）；numpy 随附；`Pillow` 仅 pytesseract 路径需要。脚本 import 失败即给出 pip 命令并退出，不自动安装。

## 数据契约与脚本

- 识别输出 JSON 按 [schemas/detection.schema.json](schemas/detection.schema.json)（schema/task/count 必填 + v2 可选超集）；字段口径见 [schemas/vision_contract_v2_camera.md](schemas/vision_contract_v2_camera.md)。
- [scripts/scripts.md](scripts/scripts.md)：camera_common / camera / recognize / vision_v2 / ocr。
- 知识库：[knowledge/knowledge.md](knowledge/knowledge.md)（硬件接口 · 识别算法 · 前后关系与遮挡线索 · OCR 后端 · 隐私合规）。

## 红线

- 每次用摄像头（含枚举）逐笔写 `<缓存>/NOTICE.md`；连拍必须用户显式声明张数；对他人拍摄先取得同意。
- 图像/审计/缓存只写平台缓存 `camera_vision/`，禁止写 skill 目录与工程目录；全链路本地不上传。
- 打不开/读帧失败立即报错，禁止重试风暴与占位黑帧；不自动换摄像头，先 list 再显式 idx。
- 缺依赖只报安装建议、经确认才装；敏感 OCR 串只报类别不复述原文。
- 悬空链接 = 0；所有 .md ≤ 50 行（50 行红线只约束 markdown 文本；脚本 .py/.ps1/.sh/.cmd 不限行数，但仍禁裸 except、print 调试残留、>100 字符长行、超长函数）；约束兜底见 [resistance/](resistance/resistance.md)。
