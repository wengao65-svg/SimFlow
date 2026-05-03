# SimFlow Visualization — 可视化 Skill

## 触发条件

- analysis 阶段完成后
- 用户请求生成图表
- 用户需要结构可视化

## 输入条件

- analysis_report.md / data_summary.json（必需）
- 可选：结构文件、轨迹文件

## 输出 Artifact

- 图表文件（PNG/PDF/SVG）
- `figure_list.json` — 图表清单
- caption 文件

## 状态写入规则

- 更新 stages.json 中 visualization 阶段状态
- 注册 artifact

## Checkpoint 规则

- 阶段完成后创建 checkpoint

## 验证项

- 图表数据来源可追溯
- caption 完整
- 格式符合论文要求
- 坐标轴标签正确

## 禁止事项

- 不要使用无法追溯的数据
- 不要省略坐标轴标签和单位
- 不要使用低分辨率图片

## 需要人工确认的场景

- 图表展示结果有歧义时
- 需要调整可视化参数时
