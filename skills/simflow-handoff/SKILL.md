---
name: simflow-handoff
description: Package artifacts and context for SimFlow handoff and delivery.
---

# SimFlow Handoff — 交付与上下文移交 Skill

## 触发条件

- 阶段完成需要生成交付摘要
- 用户请求查看当前进度
- 会话结束需要保存上下文

## 输入条件

- 当前 workflow state（必需）
- 已完成的 artifact 列表
- 最新 checkpoint

## 输出 Artifact

- handoff summary/report artifact，可按用户需要输出为 Markdown、JSON 或其他交付格式
- artifact inventory、latest checkpoint、risks、approval needs 和 next steps
- 交付内容必须能追溯到 `.simflow/state/`、artifact registry 和 checkpoint registry

## 状态写入规则

- 写入必须使用显式 `project_root` 下的 `.simflow/`
- 推荐写入 `.simflow/reports/` 或 `.simflow/artifacts/writing/`，但不要把固定文件名当成唯一合法路径
- 不要从 plugin root、MCP cwd 或 `.omx/` 推断 workflow state

## Checkpoint 规则

- 默认引用最新 checkpoint
- 如 handoff 代表阶段边界或失败交接，可创建 checkpoint，但必须记录 workflow/stage/job 关联

## 禁止事项

- 不要遗漏风险信息
- 不要省略下一步建议
- 不要在 handoff 中包含凭据
- 不要把未完成计算、未验证图表或推测性结论写成已完成事实
- 不要要求固定 `handoff.md`、`summary.json` 或 `final_handoff.md` 作为唯一交付结构

## 需要人工确认的场景

- 存在未解决的警告时
- 下一步需要用户决策时
- handoff 建议真实 local/remote/HPC submit 时
