---
name: simflow-lammps
description: Provide LAMMPS domain assistance for setup, validation, trajectory analysis, and traceable artifacts.
---

# SimFlow LAMMPS

## 触发条件

- 用户提到 LAMMPS、input script、data file、log、dump、trajectory、force field、RDF、MSD、diffusion、NVE/NVT/NPT 或 molecular dynamics。
- modeling、computation、analysis_visualization 或 writing 需要 LAMMPS-specific context。
- 用户需要检查、记录、分析或解释 LAMMPS 文件。

## 输入条件

- 用户提供的 data file、input script、log、dump、force-field parameters、artifact id、任务意图或 checkpoint。
- 可选：MDAnalysis、OVITO、Pizza.py、自写 Python、shell 命令、notebook 或用户指定工具。
- 未知或未枚举任务应返回候选路径和缺失信息，不强制归入固定 MD alias。

## 输出 Artifact

- 可选 input manifest、force-field provenance note、validation report、analysis script/output、figure/caption 或 handoff note。
- 使用任意 helper、脚本或外部工具时记录 helper-run manifest。
- artifact metadata 应记录 source data、命令/工具、参数、环境、输出和 lineage。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- LAMMPS task label 只是 recipe/tag/helper metadata，不决定顶层 workflow。
- 不自动推进固定阶段；按研究意图记录到 `modeling`、`computation` 或 `analysis_visualization`。

## Checkpoint 规则

- helper 结果可审查、可交接、可进入安全 gate 或失败时创建 checkpoint。
- checkpoint 记录力场来源、输入完整性、轨迹覆盖、统计风险和下一步。

## 禁止事项

- 不要把内置 LAMMPS helper 当成唯一合法 parser、builder 或 analysis path。
- 不要默认未知 LAMMPS 任务为固定 MD alias。
- 不要隐藏不完整力场、能量漂移、未平衡轨迹、缺失 timestep 或统计不确定性。
- 不要保存 credentials、泄露 proprietary force-field files 或私有路径。
- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。

## 需要人工确认的场景

- 力场选择、混合规则、电荷、时间步长、ensemble、约束、平衡标准或统计方法不明确。
- 涉及真实执行、远程系统、proprietary force field、credentials 或高成本资源。
- 分析方法会改变科学结论。
