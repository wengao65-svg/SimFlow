---
name: simflow-verify
description: Verify workflow state, artifacts, and readiness checks in SimFlow.
---

# SimFlow Verify — 统一验证 Skill

## 触发条件

- 阶段完成需要验证
- 用户请求验证某个 artifact
- 工作流推进需要通过验证门

## 输入条件

- 验证目标：stage 名称或 artifact 路径（必需）
- 验证规则：来自 workflow/stages/*.json 的 validators

## 输出 Artifact

- `verification_report.json` — 验证报告

## 状态写入规则

- 更新 `.simflow/state/verification.json`
- 验证失败时写入 `.simflow/reports/`

## Checkpoint 规则

- 验证失败时创建 failure checkpoint

## 禁止事项

- 不要跳过验证项
- 不要修改被验证的 artifact
- 不要在验证失败时继续推进

## 需要人工确认的场景

- 验证结果为 warning 时
- 验证规则不明确时
