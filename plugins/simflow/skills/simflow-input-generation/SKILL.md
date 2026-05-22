---
name: simflow-input-generation
description: Generate simulation input files from approved workflow plans.
---

# SimFlow Input Generation

## 触发条件

- 用户请求生成、检查、转换或修改计算输入文件。
- 旧项目仍引用 `input_generation`；新契约中它是 `computation` 阶段内的可选活动。
- 用户已提供模型、参数、软件偏好、现有输入文件或上一 checkpoint。

## 输入条件

- 用户提供的结构/模型、参数意图、软件/环境说明、现有输入或计算计划。
- 可选：ASE、pymatgen、engine helper、自写脚本、模板或用户指定工具。
- 不要求固定模型文件名、固定 builder、固定软件或固定输入结构。

## 输出 Artifact

- 输入文件、input manifest、参数记录、命令/脚本、validation report 或用户指定格式。
- 用户提供文件和生成文件应分开记录，并保留 hash 和 lineage。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 在 canonical `computation` stage 下注册输入、脚本、manifest、validation 和 hash artifact。
- 若兼容旧项目，可保留 legacy `input_generation` 标记作为 metadata，不作为顶层强制阶段。

## Checkpoint 规则

- 输入证据可审查、交接、dry-run 前或失败时创建 checkpoint。

## 验证项

- 输入文件存在性和完整性。
- 参数依据、单位、软件版本和环境说明。
- 文件格式、路径引用、licensed/proprietary 文件处理和 hash 记录。

## 禁止事项

- 不要默默替换用户提供的模型或输入文件。
- 不要把内置模板当成唯一合法输入结构。
- 不要生成、保存或泄露 credentials 或 licensed/proprietary 文件内容。

## 需要人工确认的场景

- 参数需要调整时
- 软件版本兼容性不确定时
