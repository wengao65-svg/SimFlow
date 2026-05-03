# Pre-Stage Hook

## 触发时机

每个阶段开始执行前。

## 执行步骤

1. 读取当前 workflow state
2. 加载目标阶段的 stage 配置（`workflow/stages/{stage}.json`）
3. 检查 required_inputs 是否满足
4. 检查前置阶段是否已完成（根据 workflow dependencies）
5. 如有 approval_gates，检查是否已通过

## 输出

- 输入检查报告
- 前置依赖检查报告

## 失败处理

- 输入缺失：报告缺失项，建议获取方式，中止阶段执行
- 前置阶段未完成：报告未完成阶段，建议先完成前置阶段
- 审批门未通过：报告审批状态，等待审批
