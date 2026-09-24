# resistance（约束库 / 兜底库）

本目录为 camera-vision 不可逾越的红线与降级策略。不得删除本目录中的约束条目。

## 红线

1. 每次使用摄像头（枚举/抓拍/连拍/识别取图/OCR）必须写一条 `NOTICE.md`；连拍仅当用户显式给出张数（`--n>=2`）才执行。
2. 图像、审计、一切缓存只写固定缓存目录 `camera_vision/`（`CAMERA_VISION_HOME` 可覆盖）；禁止写入 skill 目录与用户工程目录。
3. 摄像头打不开、读帧失败立即报错退出；禁止重试风暴、禁止写占位黑帧。
4. 缺依赖（opencv-python / OCR 后端）只输出 pip 安装建议，经用户确认才安装；禁止静默安装、禁止自动下载模型文件。
5. 识别输出只给结构化 JSON；OCR 命中证件号等敏感串时只报类别，不复述原文。
6. 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter；脚本英文名。

## 降级策略

- 无 cv2 → `camera_common.cv2()` 报缺依赖并给安装命令，退出。
- 无 OCR 后端 → 依次探测三后端，全缺则报三选一安装建议。
- idx 占用/不存在 → 不自动换摄像头；先 `camera.py list` 枚举，由用户/agent 明确指定 idx。
- YuNet 模型缺失 → face 直接报错并指向 `fetch_model.py --yes`（确认式）；不静默下载、不做降级假检。
- 模型下载失败/响应过小（门户劫持）→ 弃文件报错，提示手动放置 `camera_vision/models/`。
- 缓存膨胀 → 人工触发 `clean --keep-days`；无后台清理进程。
