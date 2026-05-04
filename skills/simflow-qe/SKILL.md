---
name: simflow-qe
description: Handle Quantum ESPRESSO-specific setup and execution guidance in SimFlow.
---

# SimFlow QE — Quantum ESPRESSO 专用 Skill

## 触发条件

- 用户提到 Quantum ESPRESSO / QE 计算相关任务
- input_generation 或 analysis 阶段使用 QE
- 用户请求解析 QE 输出文件

## 输入条件

- pw.x 输入文件（输入生成时）
- pw.x 输出文件（输出解析时）

## 输出 Artifact

- 输入生成：`pw.in` 文件
- 输出解析：`qe_results.json`
- SCF 收敛检查：`scf_convergence.json`

## 状态写入规则

- 注册 QE 相关 artifact
- 更新对应阶段状态

## Checkpoint 规则

- 遵循所属阶段的 checkpoint 策略

## 验证项

- 输入文件语法正确
- 赝势文件存在
- SCF 收敛性
- k 点网格合理性

## 禁止事项

- 不要使用不兼容的赝势
- 不要忽略 SCF 不收敛
- 不要省略 k 点设置说明

## 需要人工确认的场景

- 赝势选择不确定时
- SCF 不收敛需要调整时
