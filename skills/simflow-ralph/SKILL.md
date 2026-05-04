---
name: simflow-ralph
description: Drive long-running SimFlow work forward across steps and checkpoints.
---

# SimFlow Ralph — 持续推进 Skill

## 触发条件

- 长流程需要单负责人持续推进
- 用户请求自动推进直到完成或遇到审批点
- 工作流需要迭代执行

## 输入条件

- plan.json（必需）
- 当前 workflow state
- 迭代策略配置

## 输出 Artifact

- `iteration_log.json` — 迭代日志
- 各阶段 artifact

## 状态写入规则

- 持续更新 workflow state
- 记录每次迭代的状态变化

## Checkpoint 规则

- 每次迭代后创建 checkpoint

## 禁止事项

- 不要在审批点自动跳过
- 不要忽略失败继续执行
- 不要无限制迭代

## 需要人工确认的场景

- 遇到审批门时
- 连续失败超过阈值时
- 迭代次数超过上限时
