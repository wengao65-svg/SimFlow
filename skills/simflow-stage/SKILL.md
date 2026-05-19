---
name: simflow-stage
description: Execute or coordinate a single workflow stage inside SimFlow.
---

# SimFlow Stage

## 触发条件

- 用户请求从特定研究阶段独立进入。
- 需要协调一个阶段的 evidence、artifact、checkpoint 或 handoff。
- 旧项目仍引用 stage 执行；新契约以开放阶段为准。

## 输入条件

- canonical stage 名称、用户目标、已有文件、当前 `.simflow/state/` 或上一 checkpoint。
- 阶段的 acceptable inputs、evidence outputs、suggested checks 和 approval triggers。
- 不要求固定前置阶段、固定 parser、固定 builder 或固定 report 文件名。

## 输出 Artifact

- 与当前研究意图相符的 artifact、metadata、lineage、verification notes 或 handoff notes。
- 可写 `stage_report.json` 等摘要，但报告文件名不是硬性要求。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 更新 `.simflow/state/stages.json` 和 artifact registry 时记录真实 evidence 状态。
- 只协调状态和证据，不替 host agent 决定唯一科学路径。

## Checkpoint 规则

- 阶段完成、失败、交接或进入高风险动作前创建 checkpoint。

## 禁止事项

- 不要在 evidence 不足时把阶段标记为 completed。
- 不要跳过该阶段的验证门或 approval gate。
- 不要修改无关阶段状态或伪造产物。

## 需要人工确认的场景

- 输入不完整但可推断时
- 阶段执行结果有异常时
