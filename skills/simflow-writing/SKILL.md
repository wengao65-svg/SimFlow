---
name: simflow-writing
description: Write reports and narrative deliverables from SimFlow artifacts.
---

# SimFlow Writing — 写作 Skill

## 触发条件

- visualization 阶段完成后
- 用户请求生成报告或论文草稿
- 用户需要方法章节或结果讨论

## 输入条件

- 所有已完成阶段的 artifact（必需）
- figure_list.json
- references.bib

## 输出 Artifact

- `manuscript.md` — 论文草稿
- `methods.md` — 方法章节
- `results.md` — 结果讨论
- `supplementary.md` — 补充材料

## 状态写入规则

- 更新 stages.json 中 writing 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 章节完整性
- 图表引用正确
- 参考文献引用正确
- 方法描述可复现

## 禁止事项

- 不要编造实验数据
- 不要省略图表引用
- 不要忽略参考文献格式

## 需要人工确认的场景

- 论文结构需要调整时
- 关键结论需要审阅时
