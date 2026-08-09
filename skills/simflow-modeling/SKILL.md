---
name: simflow-modeling
description: Track model construction or transformation for computational simulation work.
---

## Cross-Session Experiment Memory

For work inside an existing user project, call `simflow_state/project_reentry` with the explicit canonical `project_root` before inspecting project files or performing work. Do not read or import host session transcripts as normal project memory. If the forward-only ledger has not started, call `begin_experiment` before new tracked work. Call `start_activity` before every project mutation, computation, analysis, transfer, or state change, and call `finish_activity` with outputs, outcome, failure/recovery details, and `next_action` afterward. Once the ledger is enabled, linked SimFlow writes must carry `session_context_id`, `experiment_id`, and `activity_id`. End with `session_handoff` when possible; an unclosed activity is intentionally surfaced as interrupted work on the next re-entry.

# SimFlow Modeling

## 触发条件

- 用户请求构建、导入、检查、转换、清洗、修饰或比较计算模型。
- 用户提供 POSCAR、CIF、XYZ、PDB、LAMMPS data、CP2K/VASP/QE 结构片段或其他模型来源。
- 后续 computation 或 analysis 需要结构来源、处理脚本和验证证据。

## 输入条件

- 用户提供的模型文件、文献结构、数据库结构、手写参数、上一 checkpoint 或 proposal。
- 可选：ASE、pymatgen、MDAnalysis、OVITO、VESTA、Open Babel、packmol 或用户指定工具偏好。
- 用户提供的原始模型必须保留为 source artifact，不得被静默替换。

## 输出 Artifact

- 原始模型记录、转换后模型、检查报告、处理脚本、参数记录、模型假设和 lineage。
- 模型 artifact 可以是任意合理格式，不限定为 POSCAR、CIF 或 model.json。
- 验证证据应覆盖组成、周期性、坐标、最小距离、边界条件和用户指定约束。

## 目录布局

建模工作放在 `phase3_modeling/stageN_<descriptor>/` 下，遵循
`docs/user-project-layout.md` 约定：

- 一个 `stageN_*` 目录对应一个逻辑子活动（如 `stage1_initial_models/`、
  `stage2_solvated_models/`、`stage3_supercell_build/`）。结构变体
  （不同 REE 元素、不同超胞尺寸）作为子目录，不分裂成同前缀兄弟。
- 原始用户提供的模型必须保留为 source artifact，转换后的版本作为子目录
  或带版本号的目录，不要静默覆盖。
- 处理脚本：通用版抽到项目根 `scripts/`，任务特定脚本随该 stage。
- 不要在 stage 目录内创建嵌套的 `.simflow/`；项目根 `.simflow/` 是唯一
  状态根。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 每次转换或生成模型都应记录输入、工具/脚本、参数、输出和 checksum。
- 模型来源、用户修改、agent 修改和推测性假设应分开标记。

## Checkpoint 规则

- 模型可进入 computation、需要用户审查或验证失败时创建 checkpoint。
- checkpoint 记录当前模型版本、上游来源、验证状态和剩余风险。

## 禁止事项

- 不要强制使用内置 crystal builder 或固定结构模板。
- 不要静默覆盖用户文件、丢弃原始模型或隐藏坐标/组成变更。
- 不要忽略原子重叠、异常键长、缺失元素、非中性体系或边界条件风险。

## 需要人工确认的场景

- 多个模型构造选择会改变科学问题或计算成本。
- 用户提供结构与 proposal、文献或计算软件要求不一致。
- 缺失电荷、自旋、缺陷位点、表面终止、溶剂、约束或超胞大小等关键设定。
