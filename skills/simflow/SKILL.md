# SimFlow — 总入口 Skill

## 触发条件

- 用户提到计算模拟、DFT、AIMD、MD、第一性原理、分子动力学等关键词
- 用户请求启动一个计算模拟研究项目
- 用户询问 SimFlow 能做什么

## 输入条件

- 用户自然语言描述的研究目标（必需）
- 可选：体系信息、软件偏好、计算资源

## 输出 Artifact

- `workflow_choice.json` — 选择的工作流类型（dft/aimd/md/custom）
- `intake_summary.json` — 入口分析摘要

## 状态写入规则

- 初始化 `.simflow/state/workflow.json`
- 写入 workflow 类型到 state

## Checkpoint 规则

- 不在此 skill 创建 checkpoint
- 由后续 simflow-intake 或 simflow-plan 创建

## 禁止事项

- 不要直接跳到具体阶段执行
- 不要假设用户选择的软件
- 不要在未确认工作流类型前创建 .simflow/

## 需要人工确认的场景

- 用户的研究目标不明确时
- 无法判断应使用 DFT/AIMD/MD 时
