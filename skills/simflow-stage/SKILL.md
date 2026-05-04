---
name: simflow-stage
description: Execute or coordinate a single workflow stage inside SimFlow.
---

# SimFlow Stage — 单阶段执行 Skill

## 触发条件

- 用户请求从特定阶段独立进入
- pipeline 推进到某个阶段
- 用户请求重新执行某个阶段

## 输入条件

- stage 名称（必需）
- 该 stage 的 required inputs
- 当前 workflow state

## 输出 Artifact

- 该 stage 声明的 expected outputs
- `stage_report.json` — 阶段执行报告

## 状态写入规则

- 更新 `.simflow/state/stages.json` 中对应阶段状态
- 写入阶段 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 禁止事项

- 不要在输入不满足时执行
- 不要跳过该阶段的验证门
- 不要修改其他阶段的状态

## 需要人工确认的场景

- 输入不完整但可推断时
- 阶段执行结果有异常时
