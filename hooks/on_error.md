# On-Error Hook

## 触发时机

任何阶段执行失败时。

## 执行步骤

1. 记录错误信息到 `.simflow/logs/`
2. 收集相关日志和输出
3. 创建 failure checkpoint
4. 生成错误报告
5. 通知用户

## 输出

- 错误报告
- failure checkpoint ID
- 恢复建议

## 恢复策略

- 根据阶段的 recovery_policy 决定恢复方式
- restart：从阶段开始重新执行
- from_checkpoint：从最近的 checkpoint 恢复
