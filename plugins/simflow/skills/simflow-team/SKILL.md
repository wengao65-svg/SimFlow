---
name: simflow-team
description: Coordinate parallel specialist skills working on one SimFlow objective.
---

# SimFlow Team — 并行团队 Skill

## 触发条件

- 多个独立任务可以并行执行
- 用户请求拆分任务给多个 agent
- 文献、建模、分析等任务可并行

## 输入条件

- plan.json（必需）
- 可并行的任务列表
- agent 分配策略

## 输出 Artifact

- `team_brief.json` — 团队任务分配
- `worker_reports/` — 各 worker 报告
- `team_summary.json` — 汇总结果

## 状态写入规则

- 记录各 worker 的状态
- 汇总后更新 workflow state

## Checkpoint 规则

- 每个 worker 完成后创建 checkpoint
- 汇总完成后创建总 checkpoint

## 禁止事项

- 不要给有依赖的任务分配并行
- 不要忽略 worker 间的冲突
- 不要跳过结果汇总

## 需要人工确认的场景

- worker 间结果冲突时
- 汇总结果不一致时
