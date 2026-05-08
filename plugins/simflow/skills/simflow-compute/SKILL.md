---
name: simflow-compute
description: Prepare compute execution details before simulation jobs are run.
---

# SimFlow Compute — 计算执行准备 Skill

## 触发条件

- input_generation 阶段完成后
- 用户请求准备计算任务
- 用户请求 dry-run 或提交作业

## 输入条件

- input_manifest.json（必需）
- 计算资源信息
- HPC 配置（如适用）

## 输出 Artifact

- `job_script.sh` — 作业脚本（SLURM/PBS/LSF）
- `dry_run_report.json` — dry-run 报告
- `job_record.json` — 作业记录

## 状态写入规则

- 更新 stages.json 中 compute 阶段状态
- 更新 `.simflow/state/jobs.json`

## Checkpoint 规则

- 提交前创建 checkpoint
- 完成后创建 checkpoint

## 验证项

- dry-run 通过
- 资源申请合理
- 输入文件完整
- 作业脚本语法正确

## 禁止事项

- 不要在未通过 approval gate 时真实提交
- 不要跳过 dry-run
- 不要申请过多资源

## 需要人工确认的场景

- 真实 HPC 提交前（必须）
- 资源申请异常时
- dry-run 发现问题时
