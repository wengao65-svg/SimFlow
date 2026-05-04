---
name: simflow-review
description: Review prior work and identify gaps before simulation planning continues.
---

# SimFlow Review — 综述与研究空白分析 Skill

## 触发条件

- literature 阶段完成后
- 用户请求进行文献综述分析
- 用户需要识别研究空白

## 输入条件

- literature_matrix.json（必需）
- references.bib（必需）

## 输出 Artifact

- `review.md` — 综述文档
- `gap_analysis.md` — 研究空白分析

## 状态写入规则

- 更新 stages.json 中 review 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 综述覆盖主要主题
- gap 分析有具体论据支撑
- 引用与文献矩阵一致

## 禁止事项

- 不要脱离文献矩阵编造结论
- 不要忽略争议性发现
- 不要省略方法论对比

## 需要人工确认的场景

- 研究空白判断不确定时
- 综述结论有争议时
