---
name: simflow-vasp
description: Handle VASP-specific setup and execution guidance in SimFlow.
---

# SimFlow VASP — VASP 专用 Skill

## 触发条件

- 用户提到 VASP 计算相关任务
- input_generation 或 analysis 阶段使用 VASP
- 用户请求解析 VASP 输出文件

## 输入条件

- POSCAR / INCAR / KPOINTS / POTCAR（输入生成时）
- OUTCAR / OSZICAR / vasprun.xml（输出解析时）

## 输出 Artifact

- 输入生成：INCAR, KPOINTS, POTCAR 路径
- 输出解析：`vasp_results.json`
- 收敛检查：`convergence_report.json`

## 状态写入规则

- 注册 VASP 相关 artifact
- 更新对应阶段状态

## Checkpoint 规则

- 遵循所属阶段的 checkpoint 策略

## 验证项

- INCAR 参数一致性
- KPOINTS 与 POSCAR 兼容
- POTCAR 元素顺序与 POSCAR 一致
- OUTCAR 收敛性
- OSZICAR 能量单调下降（优化）

## 禁止事项

- 不要硬编码 POTCAR 路径
- 不要忽略 ENCUT 与 POTCAR 兼容性
- 不要跳过收敛检查

## 需要人工确认的场景

- POTCAR 路径不确定时
- 收敛标准未达到时
