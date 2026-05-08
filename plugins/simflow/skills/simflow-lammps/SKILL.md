---
name: simflow-lammps
description: Handle LAMMPS-specific setup and execution guidance in SimFlow.
---

# SimFlow LAMMPS — LAMMPS 专用 Skill

## 触发条件

- 用户提到 LAMMPS / 分子动力学计算相关任务
- input_generation 或 analysis 阶段使用 LAMMPS
- 用户请求解析 LAMMPS 输出文件

## 输入条件

- data file / input script（输入生成时）
- log file / dump file（输出解析时）

## 输出 Artifact

- 输入生成：`in.lammps`, `data.*` 文件
- 输出解析：`lammps_results.json`
- 分析：RDF, MSD, diffusion 系数等

## 状态写入规则

- 注册 LAMMPS 相关 artifact
- 更新对应阶段状态

## Checkpoint 规则

- 遵循所属阶段的 checkpoint 策略

## 验证项

- 力场参数完整性
- data file 格式正确
- 时间步长合理性
- 轨迹完整性
- 温度/压力稳定性

## 禁止事项

- 不要使用不完整的力场参数
- 不要忽略能量漂移
- 不要省略平衡阶段

## 需要人工确认的场景

- 力场选择不确定时
- 体系需要特殊力场时
- MD 结果异常时
