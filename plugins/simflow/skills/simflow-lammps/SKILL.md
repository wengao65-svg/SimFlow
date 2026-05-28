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
- 如果用户只给出模糊意图，先澄清体系、力场来源、units、atom style、ensemble、timestep、equilibration/production 边界、统计方法和是否需要真实执行。

## 输出 Artifact

- 可选 input manifest、force-field provenance note、validation report、analysis script/output、figure/caption 或 handoff note。
- 使用任意 helper、脚本或外部工具时记录 helper-run manifest。
- artifact metadata 应记录 source data、命令/工具、参数、环境、输出和 lineage。
- 对 input/log/dump 审查，优先输出 inspection report：missing inputs、force-field provenance、commands detected、risk warnings、local example motif、recommended artifacts。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- LAMMPS task label 只是 recipe/tag/helper metadata，不决定顶层 workflow。
- 不自动推进固定阶段；按研究意图记录到 `modeling`、`computation` 或 `analysis_visualization`。
- 默认只做 dry-run / static inspection。真实 local、remote 或 HPC 执行必须走 SimFlow approval gate。

## 推荐检查

- 输入结构：`units`、`atom_style`、`read_data`/`create_atoms`、`pair_style`、`pair_coeff`、`run`/`minimize`/`rerun` 是否清楚。
- 力场证据：potential 文件、mixing rule、charge model、long-range electrostatics、KIM/ML potential 或 proprietary 文件来源是否记录。
- MD 风险：timestep、thermostat/barostat damping、equilibration 与 production 分段、restart/dump/thermo 间隔是否合理。
- 分析风险：RDF/MSD/VACF/viscosity/elastic 常需要统计长度、time origin、averaging method、单位转换和误差估计说明。
- 输出追踪：log、dump、restart、analysis data、plot script、figure/caption 必须能链接到输入、命令和环境。

## Optional Helper Scripts

- `scripts/inspect_lammps_inputs.py`: 静态审查 input/data/log，不运行 LAMMPS，输出 evidence-oriented JSON report。
- `scripts/generate_lammps_inputs.py`: 小范围模板助手，适合 `minimize`、`nve`、`nvt`、`npt` 初稿；未知任务返回 clarification。
- `scripts/analyze_lammps_trajectory.py`: 可选 MDAnalysis wrapper，用于 RDF/MSD 辅助分析；用户也可以自写 Python、OVITO、Pizza.py 或其他工具。

这些 helper 只是 domain assistant，不是唯一合法路径；可使用官方 LAMMPS examples 或用户自写脚本，只要记录 evidence、lineage 和风险。

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
