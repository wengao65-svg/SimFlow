# Before-Handoff Hook

## 触发时机

会话结束或 agent 交接前。

## 执行步骤

1. 检查当前 workflow 完整性
2. 列出所有已产出 artifact
3. 确认最新 checkpoint
4. 检查未解决的警告
5. 生成 handoff 摘要

## 输出

- 完整性检查报告
- artifact 清单
- 最新 checkpoint
- handoff 摘要

## 注意事项

- 不创建新 checkpoint
- 不修改 workflow state
- 不包含凭据信息
