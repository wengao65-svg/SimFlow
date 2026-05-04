---
name: simflow-handoff
description: Package artifacts and context for SimFlow handoff and delivery.
---

# SimFlow Handoff — 交付与上下文移交 Skill

## 触发条件

- 阶段完成需要生成交付摘要
- 用户请求查看当前进度
- 会话结束需要保存上下文

## 输入条件

- 当前 workflow state（必需）
- 已完成的 artifact 列表
- 最新 checkpoint

## 输出 Artifact

- `handoff.md` — 交付报告
- `summary.json` — 结构化摘要

## 状态写入规则

- 写入 `.simflow/reports/handoff/`

## Checkpoint 规则

- 不创建新 checkpoint，引用最新 checkpoint

## 禁止事项

- 不要遗漏风险信息
- 不要省略下一步建议
- 不要在 handoff 中包含凭据

## 需要人工确认的场景

- 存在未解决的警告时
- 下一步需要用户决策时
