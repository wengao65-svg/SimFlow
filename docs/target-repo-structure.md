SimFlow/
├── .codex-plugin/                         # Codex 插件元信息目录；SimFlow 作为 Codex-native 插件被发现和安装
│   └── plugin.json                        # 插件 manifest：名称、版本、描述、skills 路径、MCP 配置、权限声明
│
├── .codex/                                # Codex 本地配置；用于声明 hooks、默认策略、插件运行参数
│   ├── config.toml                        # Codex 插件运行配置，例如默认工作目录、sandbox 策略、工具权限
│   └── hooks.json                         # Codex 层面的 hook 配置，例如阶段前后触发哪些检查
│
├── AGENTS.md                              # 全局 agent 指南；定义 SimFlow 的工作原则、禁止事项、阶段推进规则
│
├── skills/                                # Codex 原生 skills；SimFlow 的主要用户入口，不再以 CLI 命令为主入口
│   ├── simflow/                           # 总入口 skill；识别用户意图并路由到具体 workflow/stage skill
│   │   ├── SKILL.md                       # 描述何时使用 SimFlow、如何选择 DFT/AIMD/MD 流程
│   │   ├── references/                    # 总体流程说明、阶段选择规则、常见任务模板
│   │   └── assets/                        # 通用提示词片段、报告模板、流程图等静态资源
│   │
│   ├── simflow-intake/                    # 入口分析 skill；判断用户从哪个研究阶段进入
│   │   ├── SKILL.md                       # 从自然语言请求中提取研究目标、体系、输入条件、模拟类型
│   │   ├── scripts/                       # 初始化 .simflow 状态、生成 workflow 草案的脚本
│   │   ├── references/                    # intake 问题清单、输入条件分类规则
│   │   └── assets/                        # intake 表单模板、workflow 初始化模板
│   │
│   ├── simflow-plan/                      # 方案规划 skill；类似 oh-my-codex 的 ralplan，但面向计算模拟
│   │   ├── SKILL.md                       # 生成可执行研究方案、阶段计划、资源估算、审批点
│   │   ├── scripts/                       # 计划结构化、阶段依赖生成、资源估算脚本
│   │   ├── references/                    # DFT/AIMD/MD 方案设计规范
│   │   └── assets/                        # proposal.md、plan.json 模板
│   │
│   ├── simflow-pipeline/                  # 工作流推进 skill；负责按 workflow 定义推进多个阶段
│   │   ├── SKILL.md                       # 读取 workflow/*.json，按阶段顺序执行、跳过、恢复或停止
│   │   ├── scripts/                       # stage transition、dependency resolution、pipeline summary
│   │   ├── references/                    # 状态机说明、阶段依赖规则
│   │   └── assets/                        # pipeline report 模板
│   │
│   ├── simflow-stage/                     # 单阶段执行 skill；用于从任意阶段独立进入
│   │   ├── SKILL.md                       # 执行指定 stage，检查输入、调用领域 skill、写 artifact、创建 checkpoint
│   │   ├── scripts/                       # 阶段执行包装器、输入解析、输出登记
│   │   ├── references/                    # stage contract 说明
│   │   └── assets/                        # stage run report 模板
│   │
│   ├── simflow-ralph/                     # 持续推进 skill；借鉴 OMX 的 ralph 思路
│   │   ├── SKILL.md                       # 长流程单负责人推进：执行、验证、失败诊断、恢复、继续
│   │   ├── scripts/                       # iteration 状态更新、失败重试、阶段摘要
│   │   ├── references/                    # long-running workflow 策略
│   │   └── assets/                        # iteration log 模板
│   │
│   ├── simflow-team/                      # 并行团队 skill；借鉴 OMX 的 team 思路
│   │   ├── SKILL.md                       # 将文献、建模、输入生成、分析、写作等任务拆给多个 agent
│   │   ├── scripts/                       # 任务拆分、worker briefing、结果汇总
│   │   ├── references/                    # 并行任务拆分策略、冲突合并规则
│   │   └── assets/                        # team brief、worker report 模板
│   │
│   ├── simflow-checkpoint/                # checkpoint 管理 skill
│   │   ├── SKILL.md                       # 创建、列出、读取、恢复 checkpoint
│   │   ├── scripts/                       # checkpoint create/restore/list 脚本
│   │   ├── references/                    # checkpoint schema 与恢复规则
│   │   └── assets/                        # checkpoint report 模板
│   │
│   ├── simflow-verify/                    # 统一验证 skill；负责调用阶段验证器
│   │   ├── SKILL.md                       # 对结构、输入文件、计算结果、分析结果、写作完整性进行验证
│   │   ├── scripts/                       # 验证器调度脚本
│   │   ├── references/                    # 各阶段质量门槛
│   │   └── assets/                        # verification report 模板
│   │
│   ├── simflow-handoff/                   # 交付与上下文移交 skill
│   │   ├── SKILL.md                       # 汇总当前 workflow 状态、artifact、风险、下一步建议
│   │   ├── scripts/                       # 生成 handoff.md、summary.json
│   │   ├── references/                    # 交付报告格式
│   │   └── assets/                        # handoff 模板
│   │
│   ├── simflow-literature/                # 文献调研阶段 skill
│   │   ├── SKILL.md                       # 文献检索、筛选、元数据整理、引用 artifact 生成
│   │   ├── scripts/                       # 文献 metadata 标准化、去重、BibTeX/CSL 处理
│   │   ├── references/                    # 文献检索策略、数据库说明
│   │   └── assets/                        # literature matrix、screening report 模板
│   │
│   ├── simflow-review/                    # 综述与研究空白分析 skill
│   │   ├── SKILL.md                       # 从文献 artifact 中提炼趋势、争议、gap、可计算问题
│   │   ├── scripts/                       # 文献矩阵聚合、主题聚类、gap summary
│   │   ├── references/                    # 综述写作和 gap 分析规范
│   │   └── assets/                        # review.md、gap_analysis.md 模板
│   │
│   ├── simflow-proposal/                  # 计算研究方案设计 skill
│   │   ├── SKILL.md                       # 设计 DFT/AIMD/MD 方案、参数、对照组、资源预算
│   │   ├── scripts/                       # 参数表生成、资源估算、方案一致性检查
│   │   ├── references/                    # DFT/AIMD/MD 参数选择指南
│   │   └── assets/                        # proposal.md、parameter_table.csv 模板
│   │
│   ├── simflow-modeling/                  # 建模 skill
│   │   ├── SKILL.md                       # 构建晶体、表面、缺陷、吸附、超胞、分子或 MD 初始结构
│   │   ├── scripts/                       # CIF/POSCAR/LAMMPS data 转换、结构检查、超胞生成
│   │   ├── references/                    # 建模规范、结构合理性规则
│   │   └── assets/                        # 结构模板、示例 POSCAR/CIF
│   │
│   ├── simflow-input-generation/          # 输入文件生成 skill
│   │   ├── SKILL.md                       # 生成 VASP/QE/LAMMPS/Gaussian 输入文件
│   │   ├── scripts/                       # INCAR/KPOINTS/POSCAR、QE input、LAMMPS input 生成器
│   │   ├── references/                    # 各软件输入语法和参数模板说明
│   │   └── assets/                        # 软件输入模板
│   │
│   ├── simflow-compute/                   # 计算执行准备 skill
│   │   ├── SKILL.md                       # 本地 dry-run、HPC 作业脚本生成、资源检查、提交前验证
│   │   ├── scripts/                       # SLURM/PBS/LSF 脚本生成、dry-run 检查、作业记录生成
│   │   ├── references/                    # HPC 提交流程和安全策略
│   │   └── assets/                        # sbatch、pbs、lsf 模板
│   │
│   ├── simflow-analysis/                  # 数据分析 skill
│   │   ├── SKILL.md                       # 解析能量、力、收敛、轨迹、RDF、MSD、扩散系数等结果
│   │   ├── scripts/                       # VASP/QE/LAMMPS/Gaussian 输出解析和统计分析脚本
│   │   ├── references/                    # 收敛性、轨迹分析、误差分析规范
│   │   └── assets/                        # analysis_report.md、CSV 模板
│   │
│   ├── simflow-visualization/             # 可视化 skill
│   │   ├── SKILL.md                       # 生成结构图、能量曲线、RDF、MSD、温度曲线、收敛图
│   │   ├── scripts/                       # matplotlib/plotly/ase/pymatgen 可视化脚本
│   │   ├── references/                    # 图表规范、论文图格式要求
│   │   └── assets/                        # figure caption 模板
│   │
│   ├── simflow-writing/                   # 写作 skill
│   │   ├── SKILL.md                       # 生成报告、论文草稿、方法章节、结果讨论、补充材料
│   │   ├── scripts/                       # artifact 汇总、引用检查、图表引用检查
│   │   ├── references/                    # 论文写作规范、章节结构
│   │   └── assets/                        # manuscript.md、methods.md、SI.md 模板
│   │
│   ├── simflow-vasp/                      # VASP 专用 skill
│   │   ├── SKILL.md                       # VASP 输入生成、OUTCAR/OSZICAR/vasprun.xml 解析、收敛检查
│   │   ├── scripts/                       # VASP 文件解析和检查脚本
│   │   ├── references/                    # VASP 参数指南
│   │   └── assets/                        # VASP 输入模板
│   │
│   ├── simflow-qe/                        # Quantum ESPRESSO 专用 skill
│   │   ├── SKILL.md                       # QE 输入生成、输出解析、收敛检查
│   │   ├── scripts/
│   │   ├── references/
│   │   └── assets/
│   │
│   ├── simflow-lammps/                    # LAMMPS 专用 skill
│   │   ├── SKILL.md                       # LAMMPS data/input 生成、轨迹解析、MD 指标分析
│   │   ├── scripts/
│   │   ├── references/
│   │   └── assets/
│   │
│   └── simflow-gaussian/                  # Gaussian 专用 skill
│       ├── SKILL.md                       # Gaussian 输入生成、log/fchk 解析、频率/能量分析
│       ├── scripts/
│       ├── references/
│       └── assets/
│
├── agents/                                # 领域 agent 角色说明；由 Codex/OMX/subagents 读取，不直接绑定模型参数
│   ├── literature_reviewer.md             # 文献调研员：检索、筛选、引用整理
│   ├── synthesizer.md                     # 综述分析员：整合文献、提炼 gap
│   ├── strategist.md                      # 方案设计师：设计 DFT/AIMD/MD 计算方案
│   ├── modeler.md                         # 建模专家：结构构建、缺陷、表面、超胞、格式转换
│   ├── input_generator.md                 # 输入生成员：VASP/QE/LAMMPS/Gaussian 输入文件
│   ├── executor.md                        # 计算执行员：HPC dry-run、作业脚本、状态跟踪
│   ├── data_analyst.md                    # 数据分析员：解析输出、收敛性、统计分析
│   ├── visualizer.md                      # 可视化专家：图表和结构可视化
│   └── writer.md                          # 写作者：论文、报告、补充材料
│
├── workflow/                              # SimFlow 的领域 workflow 定义层；相当于 .omx 里的计划/模式规则，但更面向计算模拟
│   ├── stages/                            # 单阶段声明式配置；支持从任意阶段独立进入
│   │   ├── literature.json                # 文献调研阶段：输入、输出、agent、skill、验证器、artifact 类型
│   │   ├── review.json                    # 综述分析阶段
│   │   ├── proposal.json                  # 方案设计阶段
│   │   ├── modeling.json                  # 建模阶段
│   │   ├── input_generation.json          # 输入文件生成阶段
│   │   ├── compute.json                   # 计算准备/执行阶段
│   │   ├── analysis.json                  # 结果分析阶段
│   │   ├── visualization.json             # 可视化阶段
│   │   └── writing.json                   # 写作阶段
│   │
│   ├── workflows/                         # 预定义端到端 workflow
│   │   ├── dft.json                       # DFT workflow：文献/方案/建模/输入/计算/分析/写作
│   │   ├── aimd.json                      # AIMD workflow：建模/输入/计算/轨迹分析/写作
│   │   ├── md.json                        # MD workflow：建模/力场/输入/计算/轨迹分析/写作
│   │   └── custom.schema.json             # 用户自定义 workflow 的 schema
│   │
│   ├── gates/                             # 质量门与审批门
│   │   ├── approval.json                  # 哪些动作必须人工确认，例如真实 HPC 提交、覆盖文件、使用凭据
│   │   ├── verification.json              # 阶段完成前必须通过的验证项
│   │   └── safety.json                    # 安全限制，例如禁止默认提交高成本计算
│   │
│   ├── policies/                          # 运行策略
│   │   ├── artifacts.json                 # artifact 命名、版本化、lineage 策略
│   │   ├── recovery.json                  # 失败恢复和 checkpoint 选择策略
│   │   ├── hpc.json                       # HPC dry-run、submit、status、cancel 的权限策略
│   │   ├── credentials.json               # 凭据读取规则；只声明，不存储真实密钥
│   │   └── validation.json                # 验证失败时的处理规则
│   │
│   └── templates/                         # workflow/stage 配置模板
│       ├── stage.template.json            # 新建阶段配置模板
│       ├── workflow.template.json         # 新建 workflow 模板
│       └── gate.template.json             # 新建 gate 模板
│
├── mcp/                                   # MCP 工具层；为 Codex/OMX 提供可靠工具调用，不依赖模型记忆
│   ├── .mcp.json                          # MCP server 注册配置
│   │
│   ├── servers/                           # MCP server 实现
│   │   ├── simflow_state/                 # 状态管理 MCP
│   │   │   ├── index.js                   # 读写 .simflow/state，执行状态转换
│   │   │   └── tools/                     # read_state、write_state、transition_stage 等工具
│   │   │
│   │   ├── artifact_store/                # artifact 管理 MCP
│   │   │   ├── index.js                   # 写入、读取、索引 artifact
│   │   │   └── tools/                     # write_artifact、read_artifact、lineage、list_artifacts
│   │   │
│   │   ├── checkpoint_store/              # checkpoint 管理 MCP
│   │   │   ├── index.js                   # checkpoint 创建、列出、恢复
│   │   │   └── tools/
│   │   │
│   │   ├── literature/                    # 文献数据库 MCP
│   │   │   ├── index.js                   # 文献搜索 MCP server
│   │   │   └── connectors/                # arxiv、pubmed、crossref、semantic_scholar、acs 等连接器
│   │   │
│   │   ├── structure/                     # 结构数据库与结构处理 MCP
│   │   │   ├── index.js                   # 结构检索、格式转换、结构验证
│   │   │   └── connectors/                # materials_project、cod、oqmd、icsd 等连接器
│   │   │
│   │   ├── hpc/                           # HPC 作业管理 MCP
│   │   │   ├── index.js                   # dry-run、prepare、status；真实 submit 需审批
│   │   │   └── connectors/                # slurm、pbs、lsf、本地 shell adapter
│   │   │
│   │   └── parsers/                       # 计算软件输出解析 MCP
│   │       ├── index.js                   # parser server 入口
│   │       ├── vasp/                      # VASP parser：OUTCAR、OSZICAR、vasprun.xml
│   │       ├── qe/                        # QE parser
│   │       ├── lammps/                    # LAMMPS parser
│   │       └── gaussian/                  # Gaussian parser
│   │
│   └── shared/                            # MCP 共享工具库
│       ├── auth.js                        # 凭据读取、环境变量检查、权限错误处理
│       ├── cache.js                       # 文献/结构/API 查询缓存
│       ├── retry.js                       # 重试、退避、错误分类
│       ├── transport.js                   # MCP 传输与序列化辅助
│       └── errors.js                      # 统一错误类型
│
├── runtime/                               # 本地脚本与轻量运行库；供 skills 和 MCP 调用
│   ├── lib/                               # Python 运行库；负责实际读写状态、artifact、checkpoint、验证
│   │   ├── state.py                       # .simflow/state 读写、状态转换、workflow/stage/job 结构
│   │   ├── artifact.py                    # artifact 存储、索引、版本化
│   │   ├── checkpoint.py                  # checkpoint 创建和恢复
│   │   ├── lineage.py                     # artifact 来源、依赖、参数记录
│   │   ├── verification.py                # 验证报告数据结构和执行框架
│   │   ├── environment.py                 # 本地环境探测：python、ssh、tmux、计算软件、MPI 等
│   │   ├── hpc.py                         # HPC dry-run、脚本生成、状态解析
│   │   └── utils.py                       # 通用文件、路径、时间、ID 工具
│   │
│   └── scripts/                           # 可直接被 Codex tool call / MCP / skills 调用的脚本
│       ├── init_simflow_state.py          # 初始化 .simflow/
│       ├── read_state.py                  # 读取当前 workflow/stage/job 状态
│       ├── write_state.py                 # 写入状态
│       ├── transition_stage.py            # 执行阶段状态转换
│       ├── create_checkpoint.py           # 创建 checkpoint
│       ├── restore_checkpoint.py          # 从 checkpoint 恢复
│       ├── write_artifact.py              # 写入 artifact 并登记 metadata
│       ├── list_artifacts.py              # 查询 artifact
│       ├── validate_structure.py          # 结构合理性验证
│       ├── validate_inputs.py             # 计算输入文件验证
│       ├── validate_outputs.py            # 计算输出完整性和收敛性验证
│       ├── parse_vasp.py                  # VASP 输出解析
│       ├── parse_qe.py                    # QE 输出解析
│       ├── parse_lammps.py                # LAMMPS 输出解析
│       ├── parse_gaussian.py              # Gaussian 输出解析
│       ├── generate_analysis_report.py    # 分析报告生成
│       ├── generate_handoff.py            # 交付摘要生成
│       └── detect_environment.py          # 环境能力探测
│
├── schemas/                               # 全局 JSON Schema；保证 workflow、stage、artifact、checkpoint 可验证
│   ├── workflow.schema.json               # workflow 定义 schema
│   ├── stage.schema.json                  # stage 配置 schema
│   ├── skill-contract.schema.json         # skill 输入/输出契约 schema
│   ├── artifact.schema.json               # artifact metadata schema
│   ├── checkpoint.schema.json             # checkpoint schema
│   ├── verification.schema.json           # 验证报告 schema
│   ├── hpc-job.schema.json                # HPC job record schema
│   ├── mcp-capability.schema.json         # MCP capability schema
│   ├── custom-skill-binding.schema.json   # 可选的用户自定义 Codex skill 进入 SimFlow workflow 的 binding schema
│   └── state.schema.json                  # .simflow/state schema
│
├── hooks/                                 # 事件钩子定义；不直接做复杂逻辑，复杂逻辑交给 skills/scripts/MCP
│   ├── pre_stage.md                       # 每个 stage 开始前的通用检查
│   ├── post_stage.md                      # 每个 stage 完成后的 artifact/checkpoint/report 写入要求
│   ├── pre_submit.md                      # 真实 HPC 提交前检查；必须确认 approval gate
│   ├── post_analysis.md                   # 分析完成后生成图表、报告、handoff
│   ├── on_error.md                        # 失败诊断、日志收集、checkpoint 创建
│   └── before_handoff.md                  # 交付前完整性检查
│
├── notifications/                         # 通知模板和适配说明；真实发送需用户配置凭据
│   ├── console.md                         # 控制台/对话内通知模板
│   ├── email.md                           # 邮件通知模板，不保存真实邮箱凭据
│   ├── webhook.md                         # Webhook 通知模板
│   └── notification-policy.json           # 哪些事件需要通知、通知级别
│
├── templates/                             # 用户项目初始化模板
│   ├── .simflow_structure/                # 用户工作区内 .simflow/ 目录骨架
│   │   ├── state/                         # workflow、stage、job、artifact 状态
│   │   ├── plans/                         # 研究方案和执行计划
│   │   ├── artifacts/                     # artifact 存储
│   │   ├── checkpoints/                   # checkpoint 存储
│   │   ├── reports/                       # verification、analysis、handoff 报告
│   │   ├── logs/                          # 运行日志
│   │   ├── extensions/                    # 用户项目级可选扩展；不存放 skill 本体，只存 SimFlow workflow binding
│   │   │   └── skills/                    # 用户自定义 Codex skills 的可选 SimFlow binding 文件
│   │   │       └── README.md              # 可选 binding 说明：stage、inputs、outputs、validators、checkpoint、approval；无 binding 时可由 SimFlow 尝试轻量推断
│   │   └── memory/                        # 长期项目上下文、索引和缓存
│   │
│   ├── vasp/                              # VASP 输入模板
│   │   ├── INCAR.template
│   │   ├── KPOINTS.template
│   │   ├── POSCAR.template
│   │   └── submit.slurm.template
│   │
│   ├── qe/                                # Quantum ESPRESSO 输入模板
│   │   ├── pw.in.template
│   │   └── submit.slurm.template
│   │
│   ├── lammps/                            # LAMMPS 输入模板
│   │   ├── in.lammps.template
│   │   ├── data.template
│   │   └── submit.slurm.template
│   │
│   ├── gaussian/                          # Gaussian 输入模板
│   │   ├── job.com.template
│   │   └── submit.slurm.template
│   │
│   └── reports/                           # 通用报告模板
│       ├── proposal.md.template
│       ├── model_report.md.template
│       ├── compute_plan.md.template
│       ├── analysis_report.md.template
│       ├── verification_report.md.template
│       └── handoff.md.template
│
├── docs/                                  # 项目文档
│   ├── PRD.md                             # 产品需求文档
│   ├── technical-design.md                # 技术设计文档
│   ├── workflow-layer-design.md           # SimFlow Domain Workflow Layer 设计
│   ├── skill-design.md                    # skills 设计规范
│   ├── mcp-design.md                      # MCP server 与工具设计
│   ├── state-and-checkpoint.md            # 状态和 checkpoint 设计
│   ├── artifact-schema.md                 # artifact schema 和 lineage 说明
│   ├── verification-gates.md              # 阶段验证和审批门设计
│   ├── hpc-integration.md                 # HPC / SSH / SFTP / tmux 集成策略
│   ├── custom-skills.md                   # 用户自定义 Codex skills 的边界、自动推断与可选 SimFlow binding 规则
│   ├── user_guide.md                      # 用户使用手册
│   ├── developer_guide.md                 # 开发者指南
│   └── examples/                          # 示例工作流
│       ├── dft_workflow.md                # DFT 示例
│       ├── aimd_workflow.md               # AIMD 示例
│       └── md_workflow.md                 # MD 示例
│
├── tests/                                 # 测试
│   ├── skills/                            # skill 行为测试：是否读取正确上下文、生成正确 artifact
│   ├── workflow/                          # stage/workflow 状态转换测试
│   ├── mcp/                               # MCP 工具测试
│   ├── runtime/                           # Python scripts/lib 单元测试
│   ├── schemas/                           # JSON Schema 校验测试
│   ├── e2e/                               # DFT/AIMD/MD dry-run 端到端测试
│   └── fixtures/                          # 测试数据：CIF、POSCAR、OUTCAR、LAMMPS dump、Gaussian log 等
│
├── assets/                                # 插件级静态资源
│   ├── icons/                             # 插件图标
│   ├── diagrams/                          # 工作流图、架构图
│   └── examples/                          # 可复制的示例文件
│
├── scripts/                               # 开发维护脚本，不作为用户主入口
│   ├── validate_plugin.js                 # 检查 plugin.json、skills、MCP 配置是否完整
│   ├── validate_skills.js                 # 检查每个 skill 是否包含 SKILL.md 和必要字段
│   ├── validate_schemas.js                # JSON Schema 校验
│   ├── scaffold_skill.js                  # 新建 skill 骨架
│   └── scaffold_stage.js                  # 新建 stage 配置骨架
│
├── package.json                           # 插件开发、测试、发布配置；不是主 CLI 入口
├── README.md                              # 项目说明
└── LICENSE                                # 许可证