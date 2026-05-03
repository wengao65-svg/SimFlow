# Workflow Complete Notification

## 触发条件

整个工作流所有阶段完成。

## 通知内容

- 工作流类型和 ID
- 完成的阶段列表
- 所有 artifact 摘要
- 最终报告路径

## 模板

```
[SimFlow] 工作流完成: {workflow_type}
ID: {workflow_id}
完成阶段: {completed_stages}
产出 Artifact: {artifact_count} 个
最终报告: {report_path}
```
