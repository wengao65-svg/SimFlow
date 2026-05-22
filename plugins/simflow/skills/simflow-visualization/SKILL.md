---
name: simflow-visualization
description: Compatibility entry for traceable figure and visual artifact creation.
---

# SimFlow Visualization

## 触发条件

- 用户请求图表、结构图、轨迹图、能量曲线、统计图、caption 或组会/论文插图。
- 旧项目仍引用 `visualization`；新契约属于 `analysis_visualization` 研究意图。
- 图表需要追溯到数据、脚本、参数和上游 artifact。

## 输入条件

- 分析数据、计算输出、结构/轨迹文件、figure 需求、caption 需求或用户给定样式。
- 可选：matplotlib、plotly、seaborn、OVITO、VMD、ASE、pymatgen 或用户指定工具。
- 不要求固定绘图库、固定图表格式、固定 caption 文件名或固定报告模板。

## 输出 Artifact

- 图表文件、源数据引用、绘图脚本、命令记录、caption、样式参数和 lineage。
- 图表可以是用户指定的 PNG、PDF、SVG、HTML、notebook 输出或其他合理格式。
- caption 应区分数据事实、计算条件、解释和 speculative 说明。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- 注册图表、脚本、数据、caption、环境和参数，并链接到上游 artifact。
- 图表来源必须可审查；无法追溯的数据不得用于最终结论。

## Checkpoint 规则

- 图表集可审查、可写作、可交接或失败时创建 checkpoint。
- checkpoint 记录图表版本、数据来源、脚本、格式和剩余风险。

## 禁止事项

- 不要使用无法追溯的数据生成结论图。
- 不要隐藏轴标签、单位、归一化、筛选、拟合或统计处理。
- 不要为了美观改变科学含义或掩盖异常数据。

## 需要人工确认的场景

- 可视化选择影响科学解读。
- 用户要求特定期刊、组会、报告或品牌格式。
- 图表揭示的趋势与已有证据不一致。
