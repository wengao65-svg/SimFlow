---
name: simflow-lammps
description: Provide LAMMPS domain assistance for setup, validation, MLP-MD deployment, output intake, troubleshooting, and traceable artifacts.
---

# SimFlow LAMMPS

`simflow-lammps` 是 LAMMPS domain assistant，不是 workflow executor。它负责解释、
检查和记录 LAMMPS 输入/输出证据；顶层 stage、checkpoint、approval gate 和跨 skill
handoff 仍由 SimFlow workflow 层处理。

## 触发条件

- 用户提到 LAMMPS、input script、data file、log、dump、trajectory、force field、
  RDF、MSD、diffusion、NVE/NVT/NPT/NPH、ReaxFF、DeepMD、MACE、NequIP、
  Allegro、PACE、SNAP、QUIP 或 MLP-MD。
- modeling、computation、analysis_visualization 或 writing 需要 LAMMPS-specific
  file context。
- 用户需要检查、生成草稿、记录、解释或交接 LAMMPS 文件。

## Task Routing

| Route | 用途 | 主要证据 |
| --- | --- | --- |
| `classic_md` | EAM/MEAM/Tersoff/SW/AIREBO/LJ/KIM 等经典势 MD | 势函数来源、units、atom_style、ensemble、timestep、log/dump |
| `reactive_md` | ReaxFF/COMB 等反应性或可变电荷 MD | 参数来源、电荷平衡、long-range 设置、稳定性和时间步长 |
| `mlp_md_deployment` | LAMMPS 调用已训练 MLP 模型运行 MD | model 文件、type mapping、LAMMPS package/build 证据、`simflow-mlp` handoff |
| `analysis_handoff` | LAMMPS log/dump/trajectory 输出 intake 并交给分析 stage | `lammps_output_intake_manifest`、dump columns、units、atom ids、image flags、type mapping |
| `troubleshooting` | 输入、运行、package、MPI/GPU 或物理稳定性问题 | error/warning、最小复现输入、环境和变更记录 |

MLP-MD 中本 skill 的 claim scope 是 **deployment only**：它只说明 LAMMPS 如何
引用模型并准备/检查 MD 输入，不评价 MLP 训练质量、外推安全性、验证覆盖或 production
readiness。这些证据必须交给 `simflow-mlp`。

Analysis boundary: `simflow-lammps` does not own final property analysis,
statistics, figures, or scientific claims. It records LAMMPS-specific output
semantics and hands analysis intent to `simflow-analysis-visualization`.

## 输入条件

- 用户提供的 data file、input script、log、dump、force-field parameters、模型文件元数据、
  `lmp -h` 输出、artifact id、任务意图或 checkpoint。
- 可选工具包括 MDAnalysis、OVITO、Pizza.py、自写 Python、shell 命令、notebook 或用户指定工具。
- 未知或未枚举任务应返回候选路径和缺失信息，不强制归入固定 MD alias。
- 模糊意图需要澄清体系、力场来源、units、atom style、ensemble、timestep、
  equilibration/production 边界、统计方法、是否真实执行。

## Reference Map

- `references/lammps_parameters.md`: compact index and legacy entry point.
- `references/lammps_official_sources.md`: 官方命令、package、加速、ML pair style 和错误文档入口。
- `references/lammps_input_validation.md`: input/data/log/dump 静态检查合同。
- `references/lammps_force_fields_and_mlp.md`: 经典势、反应性势、KIM、MLP 部署证据和 `simflow-mlp` 边界。
- `references/lammps_md_workflows.md`: minimize、equilibration、production、transport、rerun、restart/smoke/production。
- `references/lammps_output_intake.md`: LAMMPS log/dump/data/restart intake、`lammps_output_intake_manifest` 和 analysis handoff。
- `references/lammps_troubleshooting.md`: package 缺失、lost atoms、dangerous builds、GPU/MPI、漂移和 MLP runtime 问题。

## 输出 Artifact

- 可选 input manifest、force-field provenance note、MLP deployment manifest、validation report、
  LAMMPS output intake manifest 或 handoff note。
- 使用任意 helper、脚本或外部工具时记录 helper-run manifest。
- artifact metadata 应记录 source data、命令/工具、参数、环境、输出和 lineage。
- 对 input/log/dump 审查，优先输出 inspection report：missing inputs、force-field provenance、
  commands detected、risk warnings、local example motif、recommended artifacts。

## 状态与安全规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- LAMMPS task label 只是 recipe/tag/helper metadata，不决定顶层 workflow。
- 默认只做 dry-run / static inspection。真实 local、remote 或 HPC 执行必须走 SimFlow
  approval gate。
- MLP-MD 是 recipe/tag，不是新的顶层 stage；生产可用性 claims 必须通过 MLP/readiness evidence。

## Optional Helper Scripts

- `scripts/inspect_lammps_inputs.py`: 静态审查 input/data/log 和可选 `lmp -h` 输出，不运行 LAMMPS；
  输出 input inspection 和 MLP deployment evidence。
- `scripts/generate_lammps_inputs.py`: 小范围模板助手，适合 `minimize`、`nve`、`nvt`、`npt` 初稿；
  `mlp_md` 缺模型/type/package 证据时返回 `needs_inputs`。
- `scripts/analyze_lammps_trajectory.py`: analysis_visualization stage 可选的 LAMMPS trajectory
  helper route；从 LAMMPS skill 视角它只是格式/证据适配，不是最终性质分析标准。

这些 helper 只是 domain assistant，不是唯一合法路径；可使用官方 LAMMPS examples 或用户自写脚本，
只要记录 evidence、lineage 和风险。

## 禁止事项

- 不要把内置 LAMMPS helper 当成唯一合法 parser、builder 或 analysis path。
- 不要默认未知 LAMMPS 任务为固定 MD alias。
- 不要把 MLP 模型能被 LAMMPS 引用写成训练已验证、外推安全或 production-ready。
- 不要把 LAMMPS output intake 写成 RDF/MSD/VACF/输运/弹性等最终性质 claim；这些由
  `simflow-analysis-visualization` 处理。
- 不要隐藏不完整力场、能量漂移、未平衡轨迹、缺失 timestep 或统计不确定性。
- 不要保存 credentials、泄露 proprietary force-field/model files 或私有路径。
- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。

## 需要人工确认的场景

- 力场选择、混合规则、电荷、type mapping、时间步长、ensemble、约束、平衡标准或统计方法不明确。
- 涉及真实执行、远程系统、proprietary force field/model、credentials 或高成本资源。
- 分析方法会改变科学结论。
