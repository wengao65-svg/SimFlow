---
name: simflow-proposal
description: Design a computational research proposal from user intent and available evidence.
---

# SimFlow Proposal

## 触发条件

- 用户请求研究方案、计算计划、对照设计、可行性评估、资源估算或项目 proposal。
- 当前任务需要从文献、已有模型、已有数据或用户假设转为可执行研究计划。
- 用户可以从 proposal 阶段直接进入，无需先完成固定前置阶段。

## 输入条件

- 研究目标、背景证据、用户约束、已有 artifact、候选 recipe/tag 或上一 checkpoint。
- 可选：文献 notes、结构文件、软件偏好、资源限制、交付格式、风险偏好。
- 缺失信息应作为待澄清项记录，而不是强行选择固定 workflow。

## 输出 Artifact

- 研究方案、计算计划、假设与对照、资源估算、风险清单或用户指定格式的 proposal。
- 计划 artifact 应记录依据、假设、未决问题、可选路径和 approval triggers。
- 可选 recipe/tag 可以是 DFT、AIMD、classical MD、phonon、NEB、defect、adsorption 或 custom。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- proposal 结论应链接到文献、用户输入、模型、先前计算或分析 artifact。
- 将 recommendation、assumption、speculation 和 hard requirement 分开记录。

## Checkpoint 规则

- 计划达到可审查、可交接或可进入 modeling/computation 时创建 checkpoint。
- checkpoint 记录所选路径、未选路径、关键风险、资源假设和审批需求。

## 禁止事项

- 不要把 DFT/AIMD/MD 固定 DAG 当成唯一研究路径。
- 不要自动决定唯一软件、数据库、模型构建器、计算参数或论文结构。
- 不要隐藏不确定性、资源风险、缺失输入或需要用户审批的高风险动作。

## 需要人工确认的场景

- 研究目标、体系、精度、预算、时间线、软件许可或交付格式不明确。
- 多个合理计算路径会改变成本、风险或科学结论。
- 计划涉及真实执行、远程系统、licensed/proprietary 文件或高成本资源。
