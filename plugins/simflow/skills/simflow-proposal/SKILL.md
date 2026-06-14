---
name: simflow-proposal
description: Design a computational research proposal and protocol contract from user intent and available evidence.
---

# SimFlow Proposal

## 触发条件

- 用户请求研究方案、计算计划、对照设计、可行性评估、资源估算或项目 proposal。
- 当前任务需要从文献、已有模型、已有数据或用户假设转为可执行研究计划。
- 当前任务需要把研究计划转成可审查、可交接的实验方案/protocol contract。
- 用户可以从 proposal 阶段直接进入，无需先完成固定前置阶段。

## 输入条件

- 研究目标、背景证据、用户约束、已有 artifact、候选 recipe/tag 或上一 checkpoint。
- 可选：文献 notes、结构文件、软件偏好、资源限制、交付格式、风险偏好。
- 缺失信息应作为待澄清项记录，而不是强行选择固定 workflow。

## 输出 Artifact

- 研究方案、计算计划、假设与对照、资源估算、风险清单或用户指定格式的 proposal。
- 计划 artifact 应记录依据、假设、未决问题、可选路径和 approval triggers。
- protocol contract 应记录 objective、inputs、variables、control_groups、ordered_steps、acceptance_gates、dry_run_requirements、failure_branches、approval_triggers 和 handoff_outputs。
- 可选 recipe/tag 可以是 DFT、AIMD、classical MD、phonon、NEB、defect、adsorption 或 custom。

## Protocol Builder 边界

- simflow-proposal 是 proposal + protocol builder，不是计算执行器。
- protocol contract 描述如何把研究计划交接给 modeling/computation，但不生成最终软件输入、不提交本地/远程/HPC 任务。
- v1 protocol contract 保持跨 recipe 通用，不内置 VASP、CP2K、LAMMPS 的深度领域模板；领域细节由对应 domain skill 在后续阶段细化。
- 真实执行、远程系统、licensed/proprietary 文件或高成本资源必须继续走 dry-run 和 approval gate。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- proposal 结论应链接到文献、用户输入、模型、先前计算或分析 artifact。
- 将 recommendation、assumption、speculation 和 hard requirement 分开记录。
- protocol contract 必须把 missing input、evidence limit 和 approval trigger 显式记录，不能把待验证内容写成完成事实。

## Checkpoint 规则

- 计划达到可审查、可交接或可进入 modeling/computation 时创建 checkpoint。
- checkpoint 记录所选路径、未选路径、关键风险、资源假设、protocol gate 状态和审批需求。

## 禁止事项

- 不要把 DFT/AIMD/MD 固定 DAG 当成唯一研究路径。
- 不要自动决定唯一软件、数据库、模型构建器、计算参数或论文结构。
- 不要隐藏不确定性、资源风险、缺失输入或需要用户审批的高风险动作。
- 不要把 protocol builder 写成真实计算执行器，或绕过 computation 阶段的 dry-run-first 规则。

## 需要人工确认的场景

- 研究目标、体系、精度、预算、时间线、软件许可或交付格式不明确。
- 多个合理计算路径会改变成本、风险或科学结论。
- 计划涉及真实执行、远程系统、licensed/proprietary 文件或高成本资源。
- protocol acceptance gate、control/reference group 或关键变量选择会改变科学结论。
