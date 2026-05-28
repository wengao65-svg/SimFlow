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
- 验证依据：stage intent、evidence_outputs、artifact metadata、lineage、checkpoint、gate evidence 或用户指定检查
- 可使用 readiness diagnostics、runtime helper、用户提供脚本或第三方科学库，但必须记录 evidence

## 输出 Artifact

- verification/readiness report artifact，可按需要输出为 JSON、Markdown 或 structured result
- 每项检查必须区分直接 evidence、helper 输出和 agent interpretation

## 状态写入规则

- 只在显式 `project_root` 下更新 `.simflow/state/verification.json` 或 `.simflow/reports/`
- read-only readiness 查询不得修改 artifact 内容
- 不要从 plugin root、MCP cwd 或 `.omx/` 推断 workflow state

## Checkpoint 规则

- 验证失败时创建 failure checkpoint
- 阶段边界验证通过时可引用最近 checkpoint 或创建新的 boundary checkpoint

## 禁止事项

- 不要跳过验证项
- 不要修改被验证的 artifact
- 不要在验证失败时继续推进
- 不要要求固定 validator、固定 parser 或固定 report 文件名
- 不要把 warning 或 missing evidence 解释成 pass

## 需要人工确认的场景

- 验证结果为 warning 时
- 验证规则不明确时
- 验证会触发真实执行、远程访问、destructive operation 或 licensed/proprietary file handling 时
