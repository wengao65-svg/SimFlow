# Stage Failed Notification

## 触发条件

阶段执行失败。

## 通知内容

- 阶段名称和错误信息
- 失败原因分析
- 最新可用 checkpoint
- 恢复建议

## 模板

```
[SimFlow] 阶段失败: {stage_name}
错误: {error_message}
原因: {failure_analysis}
最新 Checkpoint: {checkpoint_id}
恢复建议: {recovery_suggestion}
```
