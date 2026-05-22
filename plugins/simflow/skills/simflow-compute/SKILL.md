---
name: simflow-compute
description: Compatibility entry for computation setup, validation, dry-run, and approval-aware submission.
---

# SimFlow Compute

## 触发条件

- 用户请求准备计算、检查输入、估算资源、生成脚本、dry-run、排队提交或记录 job。
- 旧项目仍引用 `compute`；新契约等价于 `computation` 研究意图。
- 任意 local、remote 或 HPC 真实执行需要安全 gate。

## 输入条件

- 计算 manifest、模型 artifact、输入文件、软件/环境说明、资源约束或上一 checkpoint。
- 可选：用户指定 engine、scheduler、模板、脚本、parser 或分析工具。
- 不要求固定软件、固定脚本生成器、固定 parser 或固定 stage predecessor。

## 输出 Artifact

- calculation manifest、input validation report、dry-run report、resource estimate、credential scan、script/input hash 或 job record。
- job record 只能在真实提交已获 approval 并实际执行提交后记录。
- 未提交、等待审批、dry-run-only 或失败状态必须明确标注。

## 状态写入规则

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- 注册输入、脚本、报告、环境、命令、hash、gate decision 和 job 记录，并建立 lineage。
- gate evidence 必须来自 artifact 或 state 记录，不能由布尔 context 代替。

## Checkpoint 规则

- dry-run/validation 完成、提交前审批、提交后记录或失败时创建 checkpoint。
- checkpoint 应说明当前 job 是否真实提交、在哪里运行、输入是否完整、输出是否完成。

## 禁止事项

- 不要在未通过 approval gate 时提交真实 local、remote 或 HPC job。
- 不要跳过 dry-run、credential scan、resource estimate、artifact hash 或输入验证。
- 不要保存 credentials、泄露 licensed/proprietary 文件或把未完成计算写成完成。

## 需要人工确认的场景

- 真实执行、远程访问、licensed software、proprietary files、破坏性操作或高成本资源。
- dry-run warning、资源异常、脚本变更、输入 hash 变更或审批证据不匹配。
