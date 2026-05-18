---
name: simflow-literature
description: Compatibility entry for literature review evidence tracking in SimFlow.
---

# SimFlow Literature

## 触发条件

- 用户请求文献检索、PDF 阅读、文献综述、引用整理或研究空白分析。
- 旧项目仍引用 `simflow-literature`；新契约等价于 `literature_review` 研究意图。
- 后续 proposal、modeling、computation、analysis 或 writing 需要可核验文献证据。

## 输入条件

- 研究问题、关键词、上传 PDF、DOI、已有 citation、用户指定文献源或检索约束。
- 可选：筛选标准、时间范围、全文可访问性、语言或领域范围。
- 不要求固定使用 arXiv、Crossref、Semantic Scholar、Zotero、PDF parser 或 web search。

## 输出 Artifact

- search/source log、paper notes、review summary、gap list、citation map 或用户指定格式的综述产物。
- 每个文献 artifact 应记录来源、检索式或用户来源、访问状态、metadata 和筛选依据。
- 直接引用、source claim 和 agent interpretation 应分开记录。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 注册文献 notes、引用文件、筛选报告和综述产物，并用 lineage 连接到来源。
- 无法访问全文、metadata 不完整或 citation 未核验时必须标记。

## Checkpoint 规则

- 检索完成、筛选完成、综述完成或转入 proposal/writing 前创建 checkpoint。
- checkpoint 记录纳入/排除标准、未解决文献缺口和不可访问来源。

## 禁止事项

- 不要伪造文献、DOI、作者、年份、引用、摘要、quote 或结论。
- 不要把未读全文写成已读。
- 不要把任何单一数据库、parser、citation 文件名或报告模板作为唯一合法路径。

## 需要人工确认的场景

- 检索范围、筛选标准、证据等级或综述体裁不明确。
- 关键文献无法访问、互相矛盾或 metadata 无法核验。
- 用户要求的结论超出当前文献证据。
