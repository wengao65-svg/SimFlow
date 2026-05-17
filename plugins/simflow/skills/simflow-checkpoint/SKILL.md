---
name: simflow-checkpoint
description: Create, inspect, and restore workflow checkpoints within SimFlow.
---

# SimFlow Checkpoint — Checkpoint 管理 Skill

## 触发条件

- 用户请求创建/列出/恢复 checkpoint
- 阶段完成需要保存状态
- 工作流失败需要回滚

## 输入条件

- 操作类型：create/list/restore（必需）
- create：当前 workflow state
- restore：checkpoint ID

## 输出 Artifact

- `checkpoint.json` — checkpoint 元数据
- 恢复时更新 state

## 状态写入规则

- create：写入 `.simflow/checkpoints/`
- restore：从 checkpoint 恢复 `.simflow/state/`

## Checkpoint 规则

- checkpoint 必须包含 workflow_id、stage_id、job_id
- checkpoint 必须包含时间戳和描述

## 禁止事项

- 不要创建没有关联信息的 checkpoint
- 不要覆盖已有 checkpoint
- 不要恢复到不存在的 checkpoint

## 需要人工确认的场景

- 恢复 checkpoint 会覆盖当前进度时
- checkpoint 数据不完整时
