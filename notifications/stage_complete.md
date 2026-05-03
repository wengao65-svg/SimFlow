# Stage Complete Notification

## 触发条件

阶段成功完成并通过验证。

## 通知内容

- 阶段名称和状态
- 产出 artifact 列表
- checkpoint ID
- 下一阶段建议

## 模板

```
[SimFlow] 阶段完成: {stage_name}
状态: completed
产出: {artifact_list}
Checkpoint: {checkpoint_id}
建议下一步: {next_stage}
```
