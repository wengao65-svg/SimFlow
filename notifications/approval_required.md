# Approval Required Notification

## 触发条件

触发审批门，需要用户确认。

## 通知内容

- 审批门名称
- 审批原因
- 需要确认的事项
- 超时时间

## 模板

```
[SimFlow] 需要审批: {gate_name}
原因: {reason}
需要确认: {items_to_confirm}
超时: {timeout_minutes} 分钟
```
