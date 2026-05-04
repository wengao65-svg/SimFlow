---
name: simflow-gaussian
description: Handle Gaussian-specific setup and execution guidance in SimFlow.
---

# SimFlow Gaussian — Gaussian 专用 Skill

## 触发条件

- 用户提到 Gaussian 计算相关任务
- input_generation 或 analysis 阶段使用 Gaussian
- 用户请求解析 Gaussian 输出文件

## 输入条件

- .com 输入文件（输入生成时）
- .log / .fchk 输出文件（输出解析时）

## 输出 Artifact

- 输入生成：`job.com` 文件
- 输出解析：`gaussian_results.json`
- 分析：能量、频率、优化状态

## 状态写入规则

- 注册 Gaussian 相关 artifact
- 更新对应阶段状态

## Checkpoint 规则

- 遵循所属阶段的 checkpoint 策略

## 验证项

- 输入文件语法正确
- 基组与计算方法兼容
- 优化收敛（无虚频等）
- 频率分析完整性

## 禁止事项

- 不要使用不兼容的基组/方法组合
- 不要忽略优化未收敛
- 不要省略频率分析（优化任务）

## 需要人工确认的场景

- 计算方法/基组选择不确定时
- 优化未收敛需要调整时
- 发现虚频时
