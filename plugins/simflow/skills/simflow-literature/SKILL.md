---
name: simflow-literature
description: Run literature discovery and synthesis for simulation research tasks.
---

# SimFlow Literature — 文献调研阶段 Skill

## 触发条件

- 工作流进入 literature 阶段
- 用户请求进行文献检索和调研
- 用户需要某个研究方向的文献综述

## 输入条件

- 研究目标/关键词（必需）
- 可选：时间范围、数据库偏好、语言偏好

## 输出 Artifact

- `literature_matrix.json` — 文献矩阵
- `references.bib` — BibTeX 引用文件
- `screening_report.md` — 文献筛选报告

## 状态写入规则

- 更新 stages.json 中 literature 阶段状态为 completed
- 注册 artifact 到 artifacts.json

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 引用完整性：每条文献有完整元数据
- 去重检查：无重复文献
- 覆盖度检查：关键词覆盖主要子方向

## 禁止事项

- 不要编造文献信息
- 不要跳过去重检查
- 不要省略元数据字段

## 需要人工确认的场景

- 文献数量过多需要筛选时
- 关键文献缺失时
