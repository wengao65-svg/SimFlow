---
name: simflow-gaussian
description: Provide Gaussian domain assistance for setup, validation, parsing, troubleshooting, and traceable artifacts.
---

# SimFlow Gaussian

## 触发条件

- 用户提到 Gaussian、`.com`、`.gjf`、`.log`、`.fchk`、route section、basis set、frequency、optimization、IRC、TD-DFT 或 molecular quantum chemistry。
- modeling、computation、analysis_visualization 或 writing 需要 Gaussian-specific context。
- 用户需要检查、记录、解析或解释 Gaussian 输入/输出。

## 输入条件

- 用户提供的 input/output/checkpoint metadata、任务意图、molecule/charge/multiplicity、artifact id 或 checkpoint。
- 可选：用户指定 parser、Open Babel、cclib、自写 Python、shell 命令、notebook 或官方文档入口。
- 未知或未枚举任务应返回候选路径和缺失信息，不强制归入 optimization/static/frequency。

## 输出 Artifact

- 可选 input manifest、route/basis validation note、analysis report、frequency/optimization status, figure/caption 或 handoff note。
- 使用任意 helper、脚本或外部工具时记录 helper-run manifest。
- artifact metadata 应记录来源、命令/工具、charge/multiplicity 假设、环境和 lineage。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- Gaussian task label 只是 recipe/tag/helper metadata，不决定顶层 workflow。
- 不自动推进固定阶段；按研究意图记录到 `computation` 或 `analysis_visualization`。

## Checkpoint 规则

- helper 结果可审查、可交接、可进入安全 gate 或失败时创建 checkpoint。
- checkpoint 记录输入假设、收敛/虚频/IRC 风险、缺失文件和下一步。

## 禁止事项

- 不要把 Gaussian helper 当成唯一合法 parser、builder 或 workflow path。
- 不要默认未知 Gaussian 任务为 optimization、static 或 frequency。
- 不要隐藏未收敛优化、虚频、不一致 charge/multiplicity 或缺失频率证据。
- 不要保存 credentials、泄露 licensed/proprietary files 或私有路径。
- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。

## 需要人工确认的场景

- 方法/基组、charge/multiplicity、solvation、spin state、frequency/IRC/TD-DFT 设置不明确。
- 涉及真实执行、远程系统、licensed/proprietary 文件、credentials 或高成本资源。
- 结果未收敛、不完整或支持不了用户想写的结论。
