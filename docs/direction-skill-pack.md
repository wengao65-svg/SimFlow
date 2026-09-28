# SimFlow 重构方向：从项目管理层回到 Skill Pack

> 决策记录与实施计划。用户已批准移除默认 HPC MCP、旧提交禁令和审批配置，并采用四项默认迁移决策。本文区分历史会话和已实施的目标状态；旧版 `refactor-streamlined-v2.md` 保留作讨论记录。

## 1. 产品边界

SimFlow 应是**计算模拟科研的 Agent Skill Pack**。Skill 告诉 Agent 怎样检查模型、输入、参数、收敛、输出和科学论断；Agent 帮人准备、分析、画图和写作。科学问题、参数取舍、数据所有权、实验记录及是否推进由人负责。用户要求时，Agent 可以向用户指定的 README 或实验本起草记录，但不再自建 `.simflow` 实验账本。

执行安全仍要保留：真实提交、删除、覆盖、远程写入或昂贵计算前，Agent 展示目标、脚本、命令、输入变化和资源，取得用户对当前动作的明确授权；不编造收敛、文献或作业状态；凭据和 POTCAR 内容不进仓库、日志或报告；不静默改已验证的科学参数。这是 Skill 指导和用户授权，不是哈希审批状态机。

## 2. 使用会话证据

`/mnt/d/sessions` 共 387 个 rollout。`/mnt/d/sessions/_analysis/simflow_user_msgs.jsonl` 提取了 203 条用户消息，但其中混有 SimFlow 开发、其他项目和真正的计算科研项目使用对话，不能把 203 当成独立的 SimFlow 用户样本。旧分析估计约 84 个主会话以计算科研为主体；该数字未在本轮重新标注核实。历史版本错误不能一概归因于当前 1.4.0-dev：2026-08-11 用户明确提醒，POTCAR 授权策略后来已修，MCP 也已从 7 个缩至 2 个。

| 历史工具调用（原分析口径） | 次数 | 意义 |
| --- | ---: | --- |
| `record` | 512 | 多种运行、分析、审批和观察记录 |
| `register` | 296 | 登记日志、目录、模型文件等 |
| `record_computation_evidence` | 169 | 多次被 proposal/状态门禁拒绝 |
| `checkpoint` | 124 | 包含用于交接或满足流程的恢复记录 |
| `read_state` | 118 | 常成为其它操作前置调用 |
| `record_user_override` | 107 | 绕过流程仍增加记录动作 |
| `record_analysis_evidence` | 44 | 把分析变成登记事项 |

数字来自现有 `docs/refactor-streamlined-v2.md` 的全量扫描摘要；本轮没有对 387 份原始 rollout 重新逐条计数。它们显示历史管理调用数量很高，不能单凭频次推断每次无用。更直接的证据是用户反馈：

- 2026-08-11 会话（`08/11/rollout-2026-08-11T20-56-44-019ff0e5-9292-77b1-9f12-4a12525af390.jsonl`）：Agent 每一步都重复“加载规则—检查状态—登记—审批—再登记”；内部约束变成显式 Skill/MCP/目录。
- 同一会话：六 phase 可以作新项目模板，不能强制现有项目；局部分析跟随输入，跨运行分析放最近公共父目录，项目级综合才放 phase 5，避免过细的 `analysis/` 层级。
- 2026-08-12 会话（`08/12/rollout-2026-08-12T18-48-49-019ff596-d06a-7351-97e3-e143f2f7a513.jsonl`）：Experiment Notebook 在删掉旧 ledger 后又引入接近两千行记忆与绑定逻辑；`material_action` 的 delete/move/overwrite 等分类被认为越界。
- `/mnt/d/sessions/_analysis/record_fail_samples.json` 中有 `register` 把目录当文件时报 `[Errno 21] Is a directory`、`record_analysis_evidence` 被前置门禁拒绝等实例。它们说明显式登记的失败路径确实打断过科研任务。

## 3. 同类项目：核实过的定位

以下仅陈述 2026-09-24 从公开 README 与仓库目录核实到的事实。不能从 README 未介绍账本推断项目内部不存在任何状态，也不以星数判断质量。

| 项目 | 公开形态 | 可借鉴的部分 |
| --- | --- | --- |
| [Google DeepMind Science Skills](https://github.com/google-deepmind/science-skills) | 科研任务 Skill；每个目录含 `SKILL.md`、可选 `scripts/`、`references/`；README 给出 `npx skills add`。 | 渐进加载领域知识和可选小工具。 |
| [Materials Simulation Skills](https://github.com/HeshamFS/materials-simulation-skills) | 面向计算材料与数值方法的 Skill、tools、tests，README 展示确定性 eval/CI。 | 用可测的检查与求解方法减少 Agent 猜测。 |
| [aimat-lab/agent-skills](https://github.com/aimat-lab/agent-skills) | 自包含 Skill 目录，覆盖 xtb、数据库、MD、Slurm 等；Skill 可独立安装。 | 各软件 Skill 应能单独使用。 |
| [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 多领域 Skill 库，公开 Skill tests、安全扫描与多宿主兼容性。 | 质量门侧重文档、脚本与行为边界。 |
| [Agent Skills 标准](https://agentskills.io/) | 文件夹、`SKILL.md`、可选资源的可移植约定。 | 公共接口以 Skill 目录为主。 |

还要看另一类工具：[AiiDA](https://github.com/aiidateam/aiida-core) 明确是带 provenance 的计算工作流管理器；[atomate2](https://github.com/materialsproject/atomate2) 明确会记录作业、目录与运行参数。它们证明科研计算**可以需要**数据库与工作流，但这是用户明确选择的基础设施。SimFlow 作为 Agent 指导包没有理由默认再造一套轻量 AiiDA/atomate2。

## 4. 目标结构与职责

```text
SimFlow/
├── skills/
│   ├── simflow-vasp/                # SKILL.md + references/ + 可选 scripts/
│   ├── simflow-cp2k/
│   ├── simflow-lammps/
│   ├── simflow-gpumd/
│   ├── simflow-mlp/
│   └── 其他研究任务 Skill/
├── docs/
└── tests/                        # 只测公开脚本、frontmatter 和真实行为
```

保留 VASP、CP2K、LAMMPS、GPUMD/NEP、MLP 的软件知识，文献检索、参考数据提取、建模、计算准备、分析和写作的科学方法。主文件只放触发条件、关键检查、常见失败、完成标准及按需引用；深资料放 `references/`。脚本只做输入检查、解析、转换、绘图等具体动作，默认只读或写用户指定输出，不能暗中初始化 `.simflow`、维护 registry 或自动登记。

跨会话继续工作时先读用户项目已有的 README、workflow.md、实验本、git 和实际文件；发生冲突时说明矛盾并请用户决定。旧 `.simflow/` 属于用户历史资料，新 Skill 不自动读取、迁移、改写或删除它。六 phase 仅作新项目可选模板，不作为路径门禁。

## 5. 移除与保留的具体边界

| 当前组件 | 目标 |
| --- | --- |
| 12 个 Research Task/Domain Skill | 保留并按任务重写，去掉 runtime 引用。 |
| `skills/simflow` Framework Skill | 从公共入口退役；其科学安全约束进入相关 Skill/AGENTS。 |
| `mcp/servers/simflow_state` | 不再作为产品接口；实验记录由用户项目管理。 |
| `mcp/servers/hpc` 的 plan/transfer/submit 状态机 | 不再默认发布；Agent 使用用户已有脚本，具体执行按对话授权。 |
| `runtime/simflow_core` 的 records、notebook、checkpoint、migration、gates | 在脚本解除依赖后退役。 |
| `workflow/`、`schemas/` 的状态机和门禁 | 退役；有科学内容的规则迁入 Skill references。 |
| 已验证的解析/检查/绘图脚本 | 去状态化后保留；行为与 fixture 测试一起迁移。 |

迁移基线（已解决）：最初有 13 个 Skill（含 Framework），38 个 Skill Python 脚本中有 37 个直接引用 `runtime` 或 `mcp`。因此先逐个拆出科学逻辑、验证行为，再移除旧代码；`orchestrate_*` 等替用户决定执行或写状态的脚本直接退役。现在可用 `npm run audit:skill-pack -- --strict` 检查公开边界。

## 6. 实施切片与验收

实施状态（2026-09-24）：Codex、Claude Code、OpenCode 均安装 12 个 Skill，包含各 Skill 自有的 `scripts/`、`lib/` 和 `assets/`。公开脚本已去状态化；旧 runtime、MCP、workflow、schema 源码及其专属测试、入口和示例已清退。默认 MCP 配置和旧提交权限设置已移除，版本为 1.5.0。历史研究证据与讨论文档保留，不会迁移或删除用户项目里的 `.simflow/` 数据。

迁移采用四项默认决定：每个 Skill 自带 `lib/`；普通检查只向 stdout 输出 JSON，报告仅在显式指定路径时写；退役 `orchestrate_*`、重复输入生成器和旧记录参数；无状态脚本经验证后重新纳入三种宿主的安装包。建模、分析、参考提取、MLP、VASP、CP2K、LAMMPS、GPUMD/NEP 的公开 helper 都按此边界处理。

### PR-A：公共分发改为 Skill-only

- Codex、Claude Code、OpenCode 入口只暴露 12 个任务/领域 Skill，不再启动 SimFlow MCP。
- Framework Skill 从公共入口退役。README、AGENTS、安装说明与 manifest 改叙事。
- runtime/MCP/workflow/schema 先标 legacy，不因本切片删除历史代码；公开 Skill 脚本若仍依赖 runtime，必须从 Skill-only 包中暂时排除并明确标记迁移状态。

验收：从干净安装包加载 Skill，启动时无 SimFlow MCP；执行普通阅读任务不创建 `.simflow`；安装包内没有破损脚本。用户已在本次对话中明确批准撤除默认 HPC MCP、提交禁令与旧审批配置。切片的验收重点是三种宿主均不默认注册 SimFlow MCP，且 Skill 明确遵循宿主权限与用户对具体动作的授权。

### PR-B：脚本去状态化

- 逐个把科学解析、输入检查、绘图代码与 `runtime.simflow_core` 分离。
- 删除 `--record-helper-run`、为了记录而设置的 `--project-root`、artifact/checkpoint 输出与任何 `.simflow` 写入。
- 用户可指定输出文件；纯检查不写文件。保留 VASP POTCAR 许可边界和科学验证。

验收：每个公开 helper 在临时项目中只生成用户指定文件；fixtures 验证数值、单位、异常输入和失败判读。

### PR-C：知识与质量门

- 校验 frontmatter、references 链接、脚本可运行性与官方 API 名称。
- 现有部分测试仍把 `## Use when`、`## Do not use when` 等固定标题当成通过条件，和当前 Skill 文本不一致；重写为实际行为和关键科学约束测试，不给 12 个 Skill 批量添加空泛标题。
- 为重要任务做少量确定性行为 eval：Agent 有 Skill 时应检查单位、收敛、来源和授权边界。
- 保留科研可复现性所需的用户文件引用；不创建 SimFlow 自己的哈希链。

验收：Skill 校验与脚本测试通过；不存在“先登记才能做科学工作”的前置条件。

### PR-D：清退旧层与只读诊断

- 当 PR-B 的脚本迁移通过后，从包与源码移除 runtime/MCP/workflow 状态机及对应测试和文档。
- 如需要，只提供独立只读 HPC/输出诊断脚本；不提供 SimFlow 提交控制器。

验收：公开包不含 `runtime/`、`mcp/`、`schemas/`、`workflow/`；所有公开脚本可以独立运行；旧用户项目数据未被改动。

## 7. 执行安全迁移的当前决定

用户已明确授权移除默认 HPC MCP，以及 `.codex/config.toml` 中的
`allow_shell`、`allow_hpc_submit`、`require_approval_for_submit` 设置。
真实执行改由相关 Skill 提醒 Agent 核查命令、输入、目标、资源和覆盖范围，
再由宿主权限机制及用户对具体动作的授权控制。对已在对话中授权的动作不重复
索要许可；动作范围发生实质变化时重新判断授权。

这与旧版哈希审批状态机不同：Skill 本身无法机械地拦截任意宿主 shell 命令。
因此验收不能声称“未确认提交被 SimFlow 技术上拦截”。应验证三种干净安装包
不含 SimFlow MCP 或执行器、不注入宿主权限配置、不会创建 `.simflow/`，并
在 Skill 中明确真实执行的授权边界。旧 runtime 和 HPC 状态机测试随源码退役；
科学解析、参数策略与 POTCAR 边界测试迁至 Skill 测试，另验证安装包中的独立脚本。

## 8. 成功指标与不做的事

| 指标 | 目标 |
| --- | --- |
| 普通科研指令触发的 SimFlow 状态写入 | 0 |
| Skill-only 安装包的 SimFlow MCP server | 0 |
| 用户脚本被无要求改写 | 0；需要改动时先展示 diff |
| Agent 完成一次输入准备与结果分析 | 不依赖 `.simflow`、登记、审批流水 |

不实现 SimFlow 自己的 LLM、workflow executor、实验账本或“实验版 git”；不自动迁移用户文件；不复制 AiiDA/atomate2 的数据库功能。用户确实需要工作流数据库时，Skill 可以指导其使用已选择的工具。


## 9. 迁移后的科学正确性收尾（2026-09-28）

架构解耦与科学可靠性分开验收。本轮修复晶体原型的常规晶胞与配位关系、
CP2K CIF 对称性展开及非正交晶格保留、LAMMPS atom_style 传递、NEP 标准输入
文件名，并为任务脚本添加显式覆盖选项。旧 hooks 仅保留退役说明，注册列表为空。

VASP 不再从 OSZICAR 能量、最小 XML 提取或 EIGENVAL 推断收敛；OUTCAR 使用
最后能量/力及最后 SCF 步证据，验证器分别检查电子、结构、正常结束和指定力阈值。
证据缺失不作为通过，离子步能量变化仅作诊断。轻量解析并不覆盖全部 VASP 作业类型。

测试增加晶体最近邻与配位数、非正交 CIF 转换、带电 LAMMPS 数据回读、任意文件名
NEP 数据集、覆盖拒绝以及收敛误判回归；发布包测试在源码目录之外执行实际科学
文件生成与解析。各 Skill 带依赖清单，详见 [helper dependencies](helper-dependencies.md)。
这些检查验证确定性 helper 行为，不代表真实引擎计算或全部科学场景已验证。
