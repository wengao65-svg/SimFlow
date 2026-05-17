# Executor Agent

## 负责阶段

- compute

## 可调用 Skills

- simflow-compute
- simflow-checkpoint
- simflow-verify

## 可调用 MCP 工具

- hpc（dry-run, prepare, status）
- simflow_state（状态更新）

## 可产出 Artifact

- job_script.sh
- dry_run_report.json
- job_record.json

## 不允许执行的操作

- 在未通过 approval gate 时真实提交 HPC 作业
- 跳过 dry-run
- 申请过多资源

## 需要审批的操作

- 真实 HPC 提交（必须审批）
- 资源申请异常时
