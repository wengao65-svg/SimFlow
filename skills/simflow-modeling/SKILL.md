# SimFlow Modeling — 建模 Skill

## 触发条件

- proposal 阶段完成后
- 用户请求构建计算模型
- 用户需要结构优化或超胞生成

## 输入条件

- proposal.md（必需）
- 可选：CIF/POSCAR 等结构文件

## 输出 Artifact

- `model.json` — 模型描述
- `POSCAR` / `structure.cif` — 结构文件
- `model_report.md` — 建模报告

## 状态写入规则

- 更新 stages.json 中 modeling 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 结构完整性：原子数、元素正确
- 周期性边界条件正确
- 键长在合理范围内
- 无原子重叠

## 禁止事项

- 不要使用不合理的晶格参数
- 不要忽略原子重叠检查
- 不要省略结构描述

## 需要人工确认的场景

- 结构优化结果异常时
- 超胞大小选择不确定时
