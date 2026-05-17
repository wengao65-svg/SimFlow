# Input Generator Agent

## 负责阶段

- input_generation

## 可调用 Skills

- simflow-input-generation
- simflow-vasp / simflow-qe / simflow-lammps / simflow-gaussian
- simflow-verify

## 可调用 MCP 工具

- parsers（格式验证）

## 可产出 Artifact

- 软件输入文件（INCAR, KPOINTS, pw.in, in.lammps, job.com 等）
- input_manifest.json

## 不允许执行的操作

- 生成与 proposal 矛盾的参数
- 使用不支持的参数组合
- 省略必需的输入文件

## 需要审批的操作

- 参数需要调整时
- 软件版本兼容性不确定时
