---
name: simflow-plan
description: Develop simulation study plans before execution begins.
---

# SimFlow Plan — 方案规划 Skill

## 触发条件

- intake 完成后需要制定研究方案
- 用户请求制定 DFT/AIMD/MD 计算方案
- 用户需要资源估算

## 输入条件

- intake_report.json（必需）
- 体系结构信息
- 计算资源可用情况

## 输出 Artifact

- `plan.json` — 结构化研究方案
- `proposal.md` — 方案文档
- `resource_estimate.json` — 资源估算

## 状态写入规则

- 更新 `.simflow/state/workflow.json` 中的 plan 字段
- 写入 `.simflow/plans/` 目录

## Checkpoint 规则

- 创建 checkpoint：`ckpt_002_plan`

## 禁止事项

- 不要跳过资源估算
- 不要假设计算资源无限
- 不要省略对照组设计

## 需要人工确认的场景

- 资源估算超出合理范围时
- 方案中存在高风险参数组合时
