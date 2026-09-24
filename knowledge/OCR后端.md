# OCR 后端

三选一，`ocr.py` 按 paddleocr→easyocr→pytesseract 顺序探测**已装**者；本 skill 从不自动 pip 安装（依赖体积大、改变环境须用户确认）。

## paddleocr

- 中文识别最强，PP-OCR 系列；依赖 paddlepaddle，安装体积约数百 MB。
- 首次运行自动下载模型到用户缓存目录；`lang="ch"` 兼顾中英。

## easyocr

- 多语种 80+；依赖 torch（体积 GB 级），CPU 推理可用但慢。
- `Reader(["ch_sim","en"], gpu=False)`；`readtext(detail=0)` 直接给文本列表。

## pytesseract

- 最轻：pip 包几 MB，但**另需系统级 tesseract 程序**（Windows 装 UB-Mannheim 版，含 chi_sim 语言包）。
- `image_to_string(Image.open(p), lang="chi_sim+eng")`；对照片/低对比度图明显弱于深度方案。
- 图像预处理（放大 2×、灰度、自适应阈值）能显著救回可用度。

## 选择建议

- 只偶尔识别打印体截图 → pytesseract；
- 常见拍照/屏幕中文 → paddleocr；
- 已有 torch 环境 → easyocr。
