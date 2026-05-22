---
name: simflow-modeling
description: Track model construction or transformation for computational simulation work.
---

# SimFlow Modeling

## 触发条件

- 用户请求构建、导入、检查、转换、清洗、修饰或比较计算模型。
- 用户提供 POSCAR、CIF、XYZ、PDB、LAMMPS data、CP2K/VASP/QE 结构片段或其他模型来源。
- 后续 computation 或 analysis 需要结构来源、处理脚本和验证证据。

## 输入条件

- 用户提供的模型文件、文献结构、数据库结构、手写参数、上一 checkpoint 或 proposal。
- 可选：ASE、pymatgen、MDAnalysis、OVITO、VESTA、Open Babel 或用户指定工具偏好。
- 用户提供的原始模型必须保留为 source artifact，不得被静默替换。

## 输出 Artifact

- 原始模型记录、转换后模型、检查报告、处理脚本、参数记录、模型假设和 lineage。
- 模型 artifact 可以是任意合理格式，不限定为 POSCAR、CIF 或 model.json。
- 验证证据应覆盖组成、周期性、坐标、最小距离、边界条件和用户指定约束。

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
