---
name: simflow-pipeline
description: Advance a SimFlow workflow across its staged execution pipeline.
---

# SimFlow Pipeline

## 触发条件

- 用户请求根据已确认计划推进多个研究阶段。
- 用户请求恢复中断的 SimFlow 项目并继续记录状态。
- 旧项目仍引用 pipeline；新契约仍以开放阶段和 evidence boundary 为准。

## 输入条件

- 已确认的计划、当前 `.simflow/state/`、相关 checkpoint 或用户指定阶段。
- 每个阶段的最低 evidence 要求、风险、approval triggers 和 handoff notes。
- 不要求固定 DFT/AIMD/MD DAG；recipe/tag 只作为参考路径。

## 输出 Artifact

- pipeline/status summary、阶段 handoff notes、checkpoint references 或用户指定交付物。
- 各阶段产物必须按实际研究工作注册 artifact 和 lineage。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 只推进状态和记录 evidence，不替 host agent 决定科学路径、软件、parser、builder 或报告结构。
- risky action 必须通过 gate；真实 local/remote/HPC 执行不得由 pipeline 自动绕过。

## Checkpoint 规则

- 阶段边界、失败边界、审批边界或恢复点需要 checkpoint。
- checkpoint 应记录当前阶段、artifact、lineage、gate 状态和未解决风险。

## 禁止事项

- 不要把 pipeline 当作中心化 workflow executor。
- 不要跳过验证门、approval gate、artifact metadata 或 checkpoint。
- 不要把未完成或未验证的阶段记录为 completed。

## 需要人工确认的场景

- 阶段验证失败、证据缺失或多个合理路径会改变结论时。
- `computation` 阶段涉及真实提交、远程系统、licensed/proprietary 文件或高成本资源时。
