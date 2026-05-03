# SimFlow Pipeline — 工作流推进 Skill

## 触发条件

- 用户请求按计划推进多个阶段
- 方案已确认，需要执行工作流
- 用户请求恢复中断的工作流

## 输入条件

- plan.json（必需）
- 当前 workflow state
- 可选：从指定 checkpoint 恢复

## 输出 Artifact

- `pipeline_status.json` — 流水线状态
- 各阶段 artifact（按 stage 产出）

## 状态写入规则

- 更新 `.simflow/state/workflow.json` 中的 current_stage
- 更新 `.simflow/state/stages.json` 中各阶段状态

## Checkpoint 规则

- 每个阶段完成后自动创建 checkpoint

## 禁止事项

- 不要跳过验证门
- 不要并行执行有依赖的阶段
- 不要忽略阶段失败

## 需要人工确认的场景

- 阶段验证失败时
- compute 阶段需要真实提交时
