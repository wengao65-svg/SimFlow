---
name: simflow-intake
description: Capture research goals and initialize a SimFlow workflow.
---

# SimFlow Intake

## 触发条件

- `simflow` skill 路由到此处。
- 用户需要从任意研究阶段进入 SimFlow。
- 用户提供研究目标、已有文件、当前阶段、约束或交付物。

## 输入条件

- 研究目标、阶段入口、已有 artifact、结构/文献/数据、软件偏好或计算资源约束。
- 可选 recipe/tag，例如 DFT、AIMD、classical MD、phonon、NEB、defect、custom。
- DFT/AIMD/MD 不是顶层 workflow 限制；缺失信息应作为待澄清项。

## 输出 Artifact

- intake summary、阶段建议、recipe/tag 建议、风险说明、handoff notes 或用户指定格式。
- 若初始化项目，应写入 canonical `.simflow/state/` 文件。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 初始化 canonical workflow state、stages、artifacts、checkpoints、lineage 和 reports。
- 不使用 plugin root 或 MCP cwd 作为项目根。

## Checkpoint 规则

- 初始状态、入口决策或失败边界需要 checkpoint。

## 禁止事项

- 不要跳过 `.simflow/` 初始化。
- 不要假设输入文件存在或证据已核验。
- 不要自动选择唯一 workflow type、软件、数据库、builder 或 parser。

## 需要人工确认的场景

- 体系信息不完整时
- 无法确定模拟类型时
