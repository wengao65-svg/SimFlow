---
name: simflow
description: Route computational simulation requests into the SimFlow workflow.
---

# SimFlow — 总入口 Skill

## 触发条件

- 用户提到计算模拟、DFT、AIMD、MD、第一性原理、分子动力学等关键词
- 用户请求启动一个计算模拟研究项目
- 用户询问 SimFlow 能做什么

## 输入条件

- 用户自然语言描述的研究目标（必需）
- 可选：体系信息、软件偏好、计算资源

## 输出 Artifact

- `workflow_choice.json` — 选择的工作流类型（dft/aimd/md/custom）
- `intake_summary.json` — 入口分析摘要
- `.simflow/reports/status_summary.md` — 当前项目状态摘要
- `.simflow/state/summary.json` — 结构化项目状态摘要

## 状态写入规则

- `$simflow` 初始化当前项目时，必须调用 MCP tool `simflow_state.init_workflow`
- `simflow_state.init_workflow` 必须创建并维护 `.simflow/` 作为 SimFlow workflow 主状态目录
- 必须写入 `.simflow/state/workflow.json`
- 必须创建 `.simflow/state/stages.json`
- 必须创建 `.simflow/state/artifacts.json`
- 必须创建 `.simflow/state/checkpoints.json`
- 项目状态摘要必须写入 `.simflow/reports/status_summary.md` 或 `.simflow/state/summary.json`
- `.omx/` 属于 oh-my-codex / host session 状态；可以读取上下文，但不得作为 SimFlow workflow 主状态目录，不得写入 SimFlow 主状态摘要

## Checkpoint 规则

- 不在此 skill 创建 checkpoint
- 由后续 simflow-intake 或 simflow-plan 创建

## 禁止事项

- 不要直接跳到具体阶段执行
- 不要假设用户选择的软件
- 不要把 `.omx/`、`.codex/` 或 host session 目录当作 `.simflow/` 的替代品
- 不要删除或修改已有 `.omx/`
- 不要把 `simflow_status_summary.md` 写入 `.omx/`

## 需要人工确认的场景

- 用户的研究目标不明确时
- 无法判断应使用 DFT/AIMD/MD 时
