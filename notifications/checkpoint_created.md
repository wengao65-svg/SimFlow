# Checkpoint Created Notification

## 触发条件

成功创建 checkpoint。

## 通知内容

- checkpoint ID
- 恢复状态与关联 record/run/milestone
- restart 引用与恢复说明

## 模板

```
[SimFlow] Recovery checkpoint created: {checkpoint_id}
Status: {status}
References: {recovery_references}
Resume: {resume_command}
```
