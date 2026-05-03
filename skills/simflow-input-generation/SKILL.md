# SimFlow Input Generation — 输入文件生成 Skill

## 触发条件

- modeling 阶段完成后
- 用户请求生成计算输入文件
- 用户需要修改现有输入文件

## 输入条件

- model.json / POSCAR（必需）
- proposal.md 中的参数设置（必需）
- 目标软件（VASP/QE/LAMMPS/Gaussian）

## 输出 Artifact

- 软件输入文件（INCAR, KPOINTS, pw.in, in.lammps, job.com 等）
- `input_manifest.json` — 输入文件清单

## 状态写入规则

- 更新 stages.json 中 input_generation 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 输入文件存在性
- 参数一致性（与 proposal 一致）
- 文件格式正确性
- 路径引用正确

## 禁止事项

- 不要生成与 proposal 矛盾的参数
- 不要使用不支持的参数组合
- 不要省略必需的输入文件

## 需要人工确认的场景

- 参数需要调整时
- 软件版本兼容性不确定时
