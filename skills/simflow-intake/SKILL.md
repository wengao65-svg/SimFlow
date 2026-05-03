# SimFlow Intake — 入口分析 Skill

## 触发条件

- simflow skill 路由到此处
- 用户需要从某个研究阶段进入
- 用户提供了研究目标和体系信息

## 输入条件

- 研究目标描述（必需）
- 体系信息（材料/分子名称、结构文件路径）
- 模拟类型偏好（DFT/AIMD/MD）
- 计算软件偏好（VASP/QE/LAMMPS/Gaussian）

## 输出 Artifact

- `intake_report.json` — 入口分析报告
- `workflow_draft.json` — 工作流草案

## 状态写入规则

- 初始化 `.simflow/` 目录结构
- 写入 `.simflow/state/workflow.json`
- 写入 `.simflow/state/stages.json`

## Checkpoint 规则

- 创建初始 checkpoint：`ckpt_001_intake`

## 禁止事项

- 不要跳过 .simflow/ 初始化
- 不要假设输入文件存在
- 不要自动选择工作流类型

## 需要人工确认的场景

- 体系信息不完整时
- 无法确定模拟类型时
