---
name: simflow-plan
description: Develop simulation study plans before execution begins.
---

# SimFlow Plan

## 触发条件

- 用户请求制定计算模拟研究方案、阶段计划、资源估算或风险评估。
- 用户需要从研究目标进入 proposal、modeling、computation、analysis 或 writing。
- 旧项目仍引用 plan；新契约中 recipe/tag 只是参考路径。

## 输入条件

- 研究目标、已有 artifact、用户约束、结构/文献/数据、软件偏好或资源限制。
- 可选：候选 recipe/tag，如 DFT、AIMD、classical MD、phonon、NEB、custom。
- 缺失信息应记录为待澄清项，不强制选择固定 workflow。

## 输出 Artifact

- 结构化计划、proposal、资源估算、风险清单、approval triggers 或用户指定格式。
- 计划应区分 hard requirement、assumption、recommendation 和 speculation。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 记录 recipe/tag、阶段建议、artifact 依赖、风险和 handoff notes。
- 不替 host agent 决定唯一软件、数据库、builder、parser 或论文结构。

## Checkpoint 规则

- 计划可审查、可交接或进入下一阶段时创建 checkpoint。

## 禁止事项

- 不要把 DFT/AIMD/MD 固定 DAG 当作唯一合法路径。
- 不要跳过资源、许可、proprietary 文件或真实执行风险。
- 不要隐藏不确定性、缺失输入或备选方案。

## 需要人工确认的场景

- 资源估算超出合理范围时
- 方案中存在高风险参数组合时
