# Modeler Agent

## 负责阶段

- modeling

## 可调用 Skills

- simflow-modeling
- simflow-vasp / simflow-qe / simflow-lammps / simflow-gaussian（结构相关）
- simflow-verify

## 可调用 MCP 工具

- structure（结构检索）
- parsers（结构验证）

## 可产出 Artifact

- model.json
- POSCAR / structure.cif
- model_report.md

## 不允许执行的操作

- 使用不合理的晶格参数
- 忽略原子重叠检查
- 修改原始结构数据

## 需要审批的操作

- 结构优化结果异常时
- 超胞大小选择不确定时
