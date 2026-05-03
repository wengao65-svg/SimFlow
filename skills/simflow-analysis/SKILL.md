# SimFlow Analysis — 数据分析 Skill

## 触发条件

- compute 阶段完成后
- 用户请求分析计算结果
- 用户需要收敛性检查或统计

## 输入条件

- 计算输出文件（必需）
- job_record.json
- proposal.md 中的分析目标

## 输出 Artifact

- `analysis_report.md` — 分析报告
- `data_summary.json` — 数据摘要
- 图表文件（如适用）

## 状态写入规则

- 更新 stages.json 中 analysis 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 输出完整性
- 收敛性（能量、力等）
- 轨迹完整性（MD）
- 统计显著性

## 禁止事项

- 不要忽略收敛问题
- 不要省略异常数据说明
- 不要编造分析结果

## 需要人工确认的场景

- 收敛未达到标准时
- 结果与预期偏差大时
