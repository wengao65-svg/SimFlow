# Post-Stage Hook

## 触发时机

每个阶段成功完成后。

## 执行步骤

1. 收集阶段产出的所有 artifact
2. 注册 artifact 到 artifacts.json（含版本和 lineage）
3. 更新 stages.json 中该阶段状态为 completed
4. 运行阶段验证器（validators）
5. 创建 checkpoint
6. 更新 workflow state 的 current_stage

## 输出

- artifact 注册确认
- 验证报告
- checkpoint ID

## 失败处理

- artifact 注册失败：记录错误，重试
- 验证失败：创建 failure checkpoint，不推进到下一阶段
