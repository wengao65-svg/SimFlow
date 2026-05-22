---
name: simflow-writing
description: Write evidence-traceable scientific deliverables from SimFlow artifacts.
---

# SimFlow Writing

## 触发条件

- 用户请求论文草稿、综述、proposal、组会材料、README、内部报告、方法说明、figure captions、cover letter 或其他科研文本。
- 当前任务需要把文献、模型、计算、分析、图表或用户输入转化为可审查文字。
- 用户可以从 writing 阶段直接进入，只要输入证据足够。

## 输入条件

- 可用的 literature、proposal、modeling、computation、analysis、figure 或 user-provided artifacts。
- 可选：目标读者、期刊/会议、格式、语气、长度、引用风格、章节结构或用户草稿。
- 不要求固定文档结构、固定文件名、固定模板或所有阶段都已完成。

## 输出 Artifact

- 用户指定格式的草稿、报告、说明、caption、slide text、proposal、review 或其他写作产物。
- Claim map、citation map、figure/data/script references 或其他 evidence traceability 记录。
- 未完成计算、未验证分析和 speculative 解释必须在文本中标记。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 关键科学 claim 必须链接到文献、模型、计算、分析、图表或用户输入 artifact。
- 引用、直接 quote、source claim、agent interpretation 和 speculation 应分开处理。

## Checkpoint 规则

- 草稿可审查、可交接、可提交给用户或发现证据缺口时创建 checkpoint。
- checkpoint 记录当前写作产物、证据覆盖、缺失 claim、未解决风险和下一步。

## 禁止事项

- 不要编造文献、citation、数据、图表、计算结果、收敛状态或实验事实。
- 不要把未完成计算、dry-run、计划任务或失败任务写成已完成结果。
- 不要强制生成某个固定报告文件、固定章节结构或固定 handoff 文件名。

## 需要人工确认的场景

- 文本目标、受众、格式、引用风格或结论强度不明确。
- 关键 claim 缺少证据、证据相互矛盾或只有 speculative 支持。
- 用户要求超出当前 artifact 能支持的科学结论。
