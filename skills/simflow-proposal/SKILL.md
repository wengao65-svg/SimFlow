# SimFlow Proposal — 计算研究方案设计 Skill

## 触发条件

- review 阶段完成后
- 用户请求设计计算方案
- AIMD/MD 工作流从此阶段开始

## 输入条件

- gap_analysis.md（DFT 工作流必需）
- 研究目标描述（必需）
- 体系信息

## 输出 Artifact

- `proposal.md` — 研究方案
- `parameter_table.json` — 参数表
- `resource_estimate.json` — 资源估算

## 状态写入规则

- 更新 stages.json 中 proposal 阶段状态
- 写入 `.simflow/plans/`

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 目标明确性
- 参数合理性（截断能、k 点、时间步长等）
- 资源估算合理性
- 对照组设计完整性

## 禁止事项

- 不要使用不合理的参数组合
- 不要省略资源估算
- 不要跳过对照组设计

## 需要人工确认的场景

- 参数选择有多个合理选项时
- 资源估算超出预算时
