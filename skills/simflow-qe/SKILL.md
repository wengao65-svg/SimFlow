---
name: simflow-qe
description: Provide Quantum ESPRESSO domain assistance for setup, checks, parsing, and traceable artifacts.
---

# SimFlow QE

## 触发条件

- 用户提到 Quantum ESPRESSO、QE、pw.x、ph.x、neb.x、bands.x、dos.x、`.in`、`.out`、pseudopotential、SCF、phonon、NEB、DOS 或 band structure。
- modeling、computation、analysis_visualization 或 writing 需要 QE-specific context。
- 用户需要检查、记录、转换或解释 QE 输入/输出。

## 输入条件

- 用户提供的 QE 输入/输出、赝势 metadata、结构文件、任务意图、artifact id 或 checkpoint。
- 可选：用户指定 parser、Python 脚本、ASE/pymatgen、外部工具或官方文档入口。
- 未枚举任务应返回候选路径和缺失信息，不强制归类为 SCF。

## 输出 Artifact

- 可选 input manifest、validation notes、command/environment note、analysis report、figure/caption note 或 handoff note。
- 使用任意 helper、脚本或外部工具时记录 helper-run manifest。
- artifact metadata 应记录来源、命令/工具、假设、赝势来源说明和 lineage。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- QE task label 只是 recipe/tag/helper metadata，不决定顶层 workflow。
- 不自动推进固定阶段；按研究意图记录到 `computation` 或 `analysis_visualization` 等开放阶段。

## Checkpoint 规则

- helper 结果可审查、可交接、可进入安全 gate 或失败时创建 checkpoint。
- checkpoint 记录缺失输入、赝势风险、收敛风险、未验证假设和下一步。

## 禁止事项

- 不要把 QE helper 当成唯一合法 parser、builder 或 workflow path。
- 不要默认未知 QE 任务为 SCF。
- 不要复制、泄露 licensed/proprietary 文件、credentials 或私有路径。
- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。

## 需要人工确认的场景

- 赝势选择、cutoff、k 点、smearing、spin/SOC、phonon/NEB 路径或收敛标准不明确。
- 涉及真实执行、远程系统、licensed/proprietary 文件或高成本资源。
- 结果未收敛、不完整或与计划矛盾。
