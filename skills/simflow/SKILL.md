---
name: simflow
description: Route computational simulation research requests into SimFlow's workflow layer.
---

# SimFlow

## 触发条件

- 用户提出计算模拟、材料计算、分子模拟、第一性原理、DFT、AIMD、MD、文献综述、建模、计算、分析或科研写作任务。
- 用户希望让 Codex/Claude Code 在开放科研任务中保留状态、证据、artifact、checkpoint、lineage、gate 或 handoff。
- 用户询问 SimFlow 的能力、项目初始化、阶段状态或安全边界。

## 输入条件

- 用户的研究目标、当前阶段、已有文件、约束条件或期望交付物。
- 可选：文献、结构文件、计算输入/输出、分析脚本、图表、写作草稿、软件偏好或计算资源信息。
- 如果需要写入状态，先解析当前工作目录作为 `project_root`，不得使用 plugin root 或 MCP server cwd。

## 输出 Artifact

- 入口摘要、阶段建议、recipe/tag 建议、风险说明或 handoff notes。
- `.simflow/` 状态记录、artifact metadata、checkpoint、lineage link 或 gate decision。
- 用户请求的任意科研交付物，只要其证据来源和生成过程可追溯。

## 状态写入规则

- `.simflow/` 是唯一 SimFlow workflow 状态根，所有写操作必须显式传 `project_root`。
- SimFlow 只记录阶段、证据、artifact、checkpoint、lineage、handoff 和 gate；科学判断、检索、建模、编码、分析和写作由 agent 负责。
- DFT、AIMD、MD、phonon、NEB、defect 等是 recipe/tag，不是顶层硬编码 workflow 限制。
- 用户显式指令优先于默认阶段建议，但不得绕过安全和可追溯性硬边界。

## Checkpoint 规则

- 重要阶段边界、证据边界、审查边界或失败边界需要 checkpoint。
- checkpoint 应说明当前阶段、关键 artifact、lineage、未解决风险和下一步。
- 不把未完成、未验证或未批准的工作 checkpoint 成已完成状态。

## 禁止事项

- 不要把 SimFlow 当作中心化 executor，替 agent 决定唯一文献源、软件、parser、builder、plotter 或报告结构。
- 不要编造文献、计算结果、数据、图表、citation、收敛状态或作业状态。
- 不要保存 credentials，不要泄露 licensed/proprietary 文件。
- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。

## 需要人工确认的场景

- 研究目标、阶段入口、交付格式或证据标准不明确。
- 涉及真实执行、远程系统、HPC、licensed/proprietary 文件、credentials、破坏性操作或高成本资源。
- 结论依赖缺失、不完整、未验证或相互矛盾的证据。
