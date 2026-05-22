---
name: simflow-analysis
description: Compatibility entry for analysis evidence tracking and result interpretation.
---

# SimFlow Analysis

## 触发条件

- 用户请求解析输出、检查收敛、统计轨迹、计算指标、比较数据或解释结果。
- 旧项目仍引用 `analysis`；新契约属于 `analysis_visualization` 研究意图。
- 写作、图表或 handoff 需要可追溯的结果证据。

## 输入条件

- 计算输出、日志、轨迹、表格、用户数据、分析目标、软件环境或上一 checkpoint。
- 可选：SimFlow helper、自写 Python、ASE、pymatgen、MDAnalysis、py4vasp、pandas、matplotlib 或其他可用工具。
- 不要求固定 parser、固定 schema、固定 report 文件名或固定绘图库。

## 输出 Artifact

- 分析脚本、命令记录、输入数据引用、派生数据、验证报告、结论说明或用户指定格式。
- 每个关键结论应能追溯到 source data、script、environment 和上游 artifact。
- 异常、缺失、不完整、未收敛或 speculative 解释必须显式标记。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 注册脚本、命令、输入、输出、环境和结论 artifact，并建立 lineage。
- 将 calculated result、derived interpretation 和 speculation 分开记录。

## Checkpoint 规则

- 分析结果可审查、可交接、可绘图或失败时创建 checkpoint。
- checkpoint 记录数据覆盖范围、验证状态、异常和剩余风险。

## 禁止事项

- 不要编造数据、收敛、统计显著性、图表或科学结论。
- 不要隐藏失败计算、缺失 timestep、异常 frame 或未验证 parser 假设。
- 不要把内置 helper 当成唯一合法分析路径。

## 需要人工确认的场景

- 分析方法选择会改变结论。
- 输出不完整、未收敛、互相矛盾或与计划不一致。
- 用户需要出版级统计、误差分析或领域审查。
