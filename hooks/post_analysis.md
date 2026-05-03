# Post-Analysis Hook

## 触发时机

分析阶段完成后。

## 执行步骤

1. 检查分析结果完整性
2. 检查收敛性
3. 生成数据摘要
4. 如有异常结果，触发 unexpected_results 审批门
5. 准备可视化所需数据

## 输出

- 分析完整性报告
- 收敛性报告
- 数据摘要

## 失败处理

- 收敛未达到：触发 convergence_failure 审批门
- 数据异常：触发 unexpected_results 审批门
