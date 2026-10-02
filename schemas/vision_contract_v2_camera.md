# 视觉描述契约 v2 · camera-vision 落地版

本技能识别输出的字段口径（`schemas/detection.schema.json` 为其 JSON Schema）。
全文规格见调度方 `vision_contract_v2.md`；本文件是本技能内的权威落地摘要。

## 启用方式（默认全关＝旧输出零回归）

- `recognize.py <face|qr|diff> ... --structured` 或 `--preprocess gray,edge` → 输出 v2 超集。
- `ocr.py --preprocess gray` → 灰度+自适应阈值预处理（产物写缓存目录）。
- 未带开关时，输出与 v1 逐字段一致（旧字段不删不改名）。

## 顶层字段

| 字段 | 说明 |
|---|---|
| `schema` / `task` / `count` | 必填，恒 `"detection"`（向后兼容） |
| `schema_version` | 出现即 `2`，标记 v2 超集 |
| `source` | `kind:"camera"`、`size_px`、`dpi_scale:1.0`、`image` 绝对路径 |
| `channels` | `preprocess` / `mean_rgb` / `saturation` / `contrast` / `gray_mean` / `edge_density` / `gray_hist_8` |
| `channels_b` | 仅 diff：后图 b 的通道统计 |
| `objects[]` | 见下 |
| `relations.pairs[]` | `{a, b, in_front, cues, confidence}`，`in_front:true`＝a 在前 |

## objects[] 每项

`id / type / label / confidence / bbox_px / bbox_norm / center_px / z_order / z_basis /
depth_cues / channel / emotion / affect / actionable / action_hint`

- `z_order`：**0＝最前**（离镜头最近、遮挡他者），递增向后；与 screen-vision `window_z` 同口径。
- `z_basis`：摄像头帧无窗口层级，恒 `"pixel_occlusion"`。
- `face` 任务保留旧 `boxes`，并补 `bbox_px/bbox_norm/center_px`。
- `emotion/affect` **仅 face 任务**输出且 `domain:"face"`；无情绪模型时 `emotion:null`。
  `--via-gateway` 本技能未接线 → 直接报错，拒绝硬猜（红线 4）。
- `label` 命中证件号等敏感值时只报类别，不复述原文。

## 前后关系（三线索融合，权重 0.5/0.3/0.2）

1. `occlusion`：裁剪区可见边缘凸包在相交矩形内的覆盖率，覆盖者在前。
2. `baseline_y`：框底边 `y/H`（地面假设），靠下者在前。
3. `relative_size`：同类型框面积大者在前。

`confidence = 支持方权重占比 × (0.4 + 0.2×线索数)`，上限 0.95。
线索冲突时取权重和较大方，置信度自然降低——不强行给结论。
