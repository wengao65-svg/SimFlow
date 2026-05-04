# SimFlow Domain Workflow Layer 实施 Workflow

## 1. 定位

SimFlow 的目标定位是一个 **Codex-native / OMX-style 的计算模拟领域 Workflow Layer**。

它不是独立 CLI-first 工具，也不负责自研或直接封装 LLM，而是以 `skills/` 为用户入口，以 `workflow/` 描述阶段与规则，以 `mcp/` 暴露稳定工具能力，以 `runtime/` 提供本地执行脚本，以 `.simflow/` 保存状态、artifact、checkpoint、报告和日志。

```text
Codex / OMX Host
  -> SimFlow Skills
  -> SimFlow Domain Workflow Layer
  -> MCP / Runtime Scripts
  -> .simflow State / Artifacts / Checkpoints
```

## 2. 总体开发顺序

```text
Phase 0   架构冻结
Phase 1   插件骨架
Phase 2   Skills 体系
Phase 3   Agent 角色
Phase 4   Workflow 定义
Phase 5   .simflow 状态与 artifact 规范
Phase 6   Runtime scripts
Phase 7   MCP 工具层
Phase 8   Verification / Hooks / Gates
Phase 9   Notifications / Handoff
Phase 10  领域 Stage Skills
Phase 11  软件专用 Skills
Phase 12  DFT / AIMD / MD Dry-run
Phase 13  外部系统集成
Phase 14  测试体系
Phase 15  文档与发布
```

核心原则：

```text
先做插件骨架和 workflow 规则，
再做状态、artifact、checkpoint，
再做 MCP 和 runtime，
最后做 DFT / AIMD / MD 端到端 dry-run。
```

---

# Phase 0：目标架构基线与设计边界确认

## 目标

明确 SimFlow 采用以下目标架构：

```text
Codex / OMX Host
  -> SimFlow Skills
  -> SimFlow Domain Workflow Layer
  -> MCP / Runtime Scripts
  -> .simflow State / Artifacts / Checkpoints
```

## 开发内容

1. 固化目标目录结构。
2. 明确 SimFlow 不采用主 CLI 驱动模式。
3. 明确 `skills/`、`workflow/`、`mcp/`、`runtime/`、`.simflow/` 的职责边界。
4. 明确由 Codex / OMX 宿主承担的能力：
   - LLM 推理
   - 对话交互
   - skill discovery
   - subagent 调度
   - 工具调用权限
5. 明确由 SimFlow 承担的能力：
   - 计算模拟阶段定义
   - artifact 规范
   - checkpoint 规范
   - workflow 状态
   - 验证门
   - HPC dry-run / submit gate
   - 计算软件解析器
   - 领域 skills

## 交付物

```text
docs/workflow-layer-design.md
docs/architecture-decision-record.md
README.md 目标架构说明
```

## 验收标准

- 不设计 `bin/simflow` 作为用户主入口；如后续存在 CLI，仅作为开发调试辅助。
- 文档明确 SimFlow 是 Codex-native / OMX-style domain workflow layer。
- 所有后续阶段都围绕 skills + workflow + MCP + `.simflow/` 推进。

---

# Phase 1：插件骨架与项目基线

## 目标

建立 SimFlow 作为 Codex 插件 / workflow layer 的基础骨架。

## 开发内容

1. 创建插件元信息目录：

```text
.codex-plugin/
.codex/
```

2. 建立插件 manifest：

```text
.codex-plugin/plugin.json
```

3. 建立全局行为准则：

```text
AGENTS.md
```

4. 建立开发脚本目录：

```text
scripts/
```

5. 建立基础工程配置：

```text
package.json
README.md
LICENSE
tests/
docs/
```

6. 增加结构校验机制，确保以下核心目录存在：

```text
skills/
workflow/
mcp/
runtime/
schemas/
templates/
hooks/
notifications/
```

## 交付物

```text
.codex-plugin/plugin.json
.codex/config.toml
.mcp.json
.agents/plugins/marketplace.json
.agents/skills
hooks/internal_workflow_hooks.json
AGENTS.md
package.json
README.md
scripts/validate_plugin.js
```

## 验收标准

- 项目可以被识别为插件包。
- 插件 manifest 可以通过结构校验。
- 所有一级目录职责清晰。
- 不要求任何业务 workflow 能运行。

---

# Phase 2：Skills 体系落地

## 目标

建立 SimFlow 的 skill-first 入口体系。

## 开发内容

1. 创建 workflow control skills：

```text
skills/simflow/
skills/simflow-intake/
skills/simflow-plan/
skills/simflow-pipeline/
skills/simflow-stage/
skills/simflow-ralph/
skills/simflow-team/
skills/simflow-checkpoint/
skills/simflow-verify/
skills/simflow-handoff/
```

2. 创建 domain stage skills：

```text
skills/simflow-literature/
skills/simflow-review/
skills/simflow-proposal/
skills/simflow-modeling/
skills/simflow-input-generation/
skills/simflow-compute/
skills/simflow-analysis/
skills/simflow-visualization/
skills/simflow-writing/
```

3. 创建 software-specific skills：

```text
skills/simflow-vasp/
skills/simflow-qe/
skills/simflow-lammps/
skills/simflow-gaussian/
```

4. 每个 skill 至少完成：

```text
SKILL.md
scripts/
references/
assets/
```

5. 每个 `SKILL.md` 必须包含：
   - 触发条件
   - 输入条件
   - 输出 artifact
   - 状态写入规则
   - checkpoint 规则
   - 禁止事项
   - 需要人工确认的场景

6. 明确用户自定义 Codex skills 的边界：
   - 用户自定义 skill 的存放、发现、安装、加载和执行由 Codex 官方机制负责。
   - SimFlow 不实现 custom skill manager、installer、loader 或 executor。
   - 用户自定义 skill 如需参与 SimFlow workflow，优先由 SimFlow 根据 skill name、description、用户请求和当前 stage 做轻量推断。
   - 如果推断结果明确，SimFlow 可将该 skill 临时绑定到对应 stage，并继续完成 artifact、verification、checkpoint 和 handoff 记录。
   - 只有复杂或严格 workflow 场景，才通过 SimFlow binding 规则显式声明其 stage、inputs、outputs、artifact、verification、checkpoint 和 approval。

## 交付物

```text
skills/*/SKILL.md
docs/skill-design.md
docs/custom-skills.md
schemas/skill-contract.schema.json
scripts/validate_skills.js
```

## 验收标准

- 所有核心 skills 目录存在。
- 每个 skill 都有 `SKILL.md`。
- 每个 skill 的用途边界清楚。
- 能区分 workflow control skill、domain stage skill、software-specific skill。

---

# Phase 3：Agent 角色体系落地

## 目标

定义 SimFlow 领域 agent，而不是绑定具体模型参数。

## 开发内容

1. 创建 agent 角色说明：

```text
agents/literature_reviewer.md
agents/synthesizer.md
agents/strategist.md
agents/modeler.md
agents/input_generator.md
agents/executor.md
agents/data_analyst.md
agents/visualizer.md
agents/writer.md
```

2. 明确每个 agent 的：
   - 负责阶段
   - 可调用 skills
   - 可调用 MCP 工具
   - 可产出 artifact
   - 不允许执行的操作
   - 需要审批的操作

3. 建立 agent 与 skill 的映射表。
4. 建立 agent 与 workflow stage 的映射表。

## 交付物

```text
agents/*.md
docs/agents-and-skills-matrix.md
workflow/policies/agent-policy.json
```

## 验收标准

- 每个阶段都有明确默认 agent。
- 每个 agent 都有明确权限边界。
- 不出现 model、temperature、provider 等 LLM 参数作为核心配置。
- agent 只描述角色行为，不实现模型调用。

---

# Phase 4：Workflow 定义层落地

## 目标

建立 SimFlow 的声明式 workflow layer。

## 开发内容

1. 创建阶段定义：

```text
workflow/stages/literature.json
workflow/stages/review.json
workflow/stages/proposal.json
workflow/stages/modeling.json
workflow/stages/input_generation.json
workflow/stages/compute.json
workflow/stages/analysis.json
workflow/stages/visualization.json
workflow/stages/writing.json
```

2. 每个 stage 定义：
   - stage name
   - description
   - default agent
   - default skill
   - required inputs
   - optional inputs
   - expected outputs
   - artifact types
   - validators
   - approval gates
   - checkpoint policy
   - recovery policy

3. 创建预设 workflow：

```text
workflow/workflows/dft.json
workflow/workflows/aimd.json
workflow/workflows/md.json
```

4. 创建 gate 定义：

```text
workflow/gates/approval.json
workflow/gates/verification.json
workflow/gates/safety.json
```

5. 创建 policy 定义：

```text
workflow/policies/artifacts.json
workflow/policies/recovery.json
workflow/policies/hpc.json
workflow/policies/credentials.json
workflow/policies/validation.json
```

6. 定义用户自定义 Codex skill 的 SimFlow workflow 轻量推断与可选 binding 规则：
   - 无 binding 文件时，SimFlow 可根据 skill name、description、用户请求和当前 stage 轻量推断该 Codex skill 如何进入 SimFlow workflow。
   - 推断结果明确时，不要求普通用户手写 binding 文件。
   - 推断不明确时，SimFlow 只询问必要信息，例如 stage、expected outputs 或是否需要 checkpoint。
   - binding 文件是复杂或严格 workflow 场景下的可选高级契约，只声明该 Codex skill 如何进入 SimFlow workflow。
   - binding 文件不存放 skill 本体。
   - 存在 binding 文件时，SimFlow 只校验 binding 中的 stage、inputs、outputs、validators、checkpoint_policy 和 approval_required。
   - Codex 仍负责发现、加载和执行用户自定义 skill。

## 交付物

```text
workflow/stages/*.json
workflow/workflows/*.json
workflow/gates/*.json
workflow/policies/*.json
schemas/stage.schema.json
schemas/workflow.schema.json
schemas/custom-skill-binding.schema.json
```

## 验收标准

- DFT / AIMD / MD 三条 workflow 能被静态解析。
- 每个 stage 都支持独立进入。
- 每个 stage 都声明输入、输出、验证器和 checkpoint 策略。
- compute 阶段默认不允许真实提交 HPC 作业，必须经过 approval gate。

---

# Phase 5：`.simflow/` 状态与产物规范落地

## 目标

定义用户项目中的运行状态、artifact、checkpoint、report 存储规范。

## 开发内容

1. 创建 `.simflow/` 模板结构：

```text
templates/.simflow_structure/
├── state/
├── plans/
├── artifacts/
├── checkpoints/
├── reports/
├── logs/
├── extensions/
│   └── skills/
└── memory/
```

2. 定义 workflow state：

```text
.simflow/state/workflow.json
```

3. 定义 stage state：

```text
.simflow/state/stages.json
```

4. 定义 job state：

```text
.simflow/state/jobs.json
```

5. 定义 artifact index：

```text
.simflow/state/artifacts.json
```

6. 定义 verification state：

```text
.simflow/state/verification.json
```

7. 定义 checkpoint 目录和命名规则。
8. 定义 artifact 版本化规则和 lineage 规则。
9. 定义 `.simflow/extensions/skills/` 作为用户自定义 Codex skills 的可选项目级 SimFlow binding 目录。

## 交付物

```text
templates/.simflow_structure/
schemas/state.schema.json
schemas/artifact.schema.json
schemas/checkpoint.schema.json
docs/state-and-checkpoint.md
docs/artifact-schema.md
```

## 验收标准

- `.simflow/` 结构可初始化。
- `.simflow/extensions/skills/` 可作为项目级 custom skill binding 目录，但普通用户不需要默认手写 binding 文件。
- workflow、stage、job、artifact、checkpoint 都有 schema。
- artifact 不允许无 metadata 写入。
- checkpoint 不允许缺失 workflow/stage/job 关联。

---

# Phase 6：Runtime Scripts 与轻量运行库骨架落地

## 目标

建立 skills 和 MCP 可调用的本地执行能力，但不做主 CLI。

## 开发内容

1. 创建 Python runtime library：

```text
runtime/lib/state.py
runtime/lib/artifact.py
runtime/lib/checkpoint.py
runtime/lib/lineage.py
runtime/lib/verification.py
runtime/lib/environment.py
runtime/lib/hpc.py
runtime/lib/utils.py
```

2. 创建可调用脚本：

```text
runtime/scripts/init_simflow_state.py
runtime/scripts/read_state.py
runtime/scripts/write_state.py
runtime/scripts/transition_stage.py
runtime/scripts/create_checkpoint.py
runtime/scripts/restore_checkpoint.py
runtime/scripts/write_artifact.py
runtime/scripts/list_artifacts.py
runtime/scripts/validate_structure.py
runtime/scripts/validate_inputs.py
runtime/scripts/validate_outputs.py
runtime/scripts/parse_vasp.py
runtime/scripts/parse_qe.py
runtime/scripts/parse_lammps.py
runtime/scripts/parse_gaussian.py
runtime/scripts/generate_analysis_report.py
runtime/scripts/generate_handoff.py
runtime/scripts/detect_environment.py
```

3. 明确 runtime scripts 只作为：
   - skill helper
   - MCP backend
   - validation backend
   - artifact/state/checkpoint backend

4. 明确 runtime scripts 不承担用户主入口职责。

## 交付物

```text
runtime/lib/
runtime/scripts/
docs/runtime-design.md
tests/runtime/
```

## 验收标准

- 所有 runtime 能力有明确入口脚本。
- 每个脚本有输入输出契约。
- runtime 可以被 skills 或 MCP 调用。
- 不规划 `simflow run` 作为用户主 workflow 入口。

---

# Phase 7：MCP 工具层落地

## 目标

建立 SimFlow 可被 Codex / OMX 稳定调用的工具接口。

## 开发内容

1. 创建 MCP 配置：

```text
.mcp.json
```

2. 创建核心状态工具 MCP：

```text
mcp/servers/simflow_state/
mcp/servers/artifact_store/
mcp/servers/checkpoint_store/
```

3. 创建领域 MCP：

```text
mcp/servers/literature/
mcp/servers/structure/
mcp/servers/hpc/
mcp/servers/parsers/
```

4. 创建共享工具：

```text
mcp/shared/auth.js
mcp/shared/cache.js
mcp/shared/retry.js
mcp/shared/transport.js
mcp/shared/errors.js
```

5. 第一版所有外部能力采用 mock / dry-run 策略：
   - 文献检索 mock
   - 结构数据库 mock
   - HPC dry-run
   - parser sample fixtures

6. 明确真实外部系统接入边界：
   - API key 不写入仓库
   - SSH 凭据不写入仓库
   - HPC submit 默认禁用
   - submit 必须通过 approval gate

## 交付物

```text
.mcp.json
mcp/servers/*
mcp/shared/*
schemas/mcp-capability.schema.json
docs/mcp-design.md
tests/mcp/
```

## 验收标准

- MCP registry 能列出 SimFlow 工具能力。
- 状态、artifact、checkpoint 三类工具优先可用。
- HPC 工具默认只支持 dry-run。
- 所有需要凭据的工具都有安全边界说明。

---

# Phase 8：Verification Gates 与 Hooks 落地

## 目标

建立阶段完成前后的质量门、审批门和事件钩子。

## 开发内容

1. 创建验证 gate：

```text
workflow/gates/verification.json
```

2. 创建审批 gate：

```text
workflow/gates/approval.json
```

3. 创建安全 gate：

```text
workflow/gates/safety.json
```

4. 创建 hooks：

```text
hooks/pre_stage.md
hooks/post_stage.md
hooks/pre_submit.md
hooks/post_analysis.md
hooks/on_error.md
hooks/before_handoff.md
```

5. 定义验证报告结构：

```text
schemas/verification.schema.json
```

6. 定义各阶段验证目标：
   - literature：引用完整性、重复文献、元数据缺失
   - proposal：目标明确性、参数合理性、资源估算
   - modeling：结构完整性、元素、周期性、键长异常
   - input_generation：输入文件存在性、参数一致性
   - compute：dry-run、资源申请、submit gate
   - analysis：输出完整性、收敛性、轨迹完整性
   - visualization：图表数据来源、caption、格式
   - writing：章节完整性、图表引用、参考文献引用

## 交付物

```text
hooks/*.md
workflow/gates/*.json
schemas/verification.schema.json
docs/verification-gates.md
tests/workflow/verification*
```

## 验收标准

- 每个 stage 都绑定至少一个 verification gate。
- compute 阶段绑定 pre_submit gate。
- 验证失败时必须写入 report。
- 失败时必须创建 checkpoint 或 failure snapshot。
- 真实 HPC submit 必须人工确认。

---

# Phase 9：通知与 Handoff 机制落地

## 目标

建立 workflow 执行过程中的状态通知和交付机制。

## 开发内容

1. 创建通知策略：

```text
notifications/notification-policy.json
```

2. 创建通知模板：

```text
notifications/console.md
notifications/email.md
notifications/webhook.md
```

3. 明确默认通知渠道：
   - 对话内通知
   - console-style summary
   - handoff report

4. 邮件和 webhook 仅保留模板与配置方式，不默认真实发送。

5. 建立 handoff skill 输出标准：
   - 当前阶段
   - 已完成阶段
   - 当前 artifact
   - 当前 checkpoint
   - 验证结果
   - 风险
   - 下一步建议
   - 是否需要用户审批

## 交付物

```text
notifications/*
skills/simflow-handoff/
templates/reports/handoff.md.template
docs/handoff-and-notification.md
```

## 验收标准

- 每次阶段完成后可以生成阶段摘要。
- 每次失败后可以生成错误摘要。
- handoff 能让用户或新 agent 恢复上下文。
- 不需要真实邮箱或 webhook 凭据即可完成默认交付。

---

# Phase 10：领域 Stage Skills 落地

## 目标

让每个计算模拟研究阶段具备可用的 skill 入口。

## 开发内容

完成以下阶段 skill 的契约、骨架、绑定关系与最小可用入口：

```text
simflow-literature
simflow-review
simflow-proposal
simflow-modeling
simflow-input-generation
simflow-compute
simflow-analysis
simflow-visualization
simflow-writing
```

每个 stage skill 需要完成：

1. 输入 artifact 类型定义。
2. 输出 artifact 类型定义。
3. 与 workflow stage 的绑定。
4. 与 agent 的绑定。
5. 与 MCP 工具的绑定。
6. 与 verification gate 的绑定。
7. 与 checkpoint 策略的绑定。
8. 与 handoff 输出的绑定。

## 交付物

```text
skills/simflow-literature/
skills/simflow-review/
skills/simflow-proposal/
skills/simflow-modeling/
skills/simflow-input-generation/
skills/simflow-compute/
skills/simflow-analysis/
skills/simflow-visualization/
skills/simflow-writing/
docs/stage-contracts.md
tests/skills/
```

## 验收标准

- 每个阶段可以被单独触发。
- 每个阶段可以声明缺失输入。
- 每个阶段可以产出 artifact。
- 每个阶段可以触发验证。
- 每个阶段可以创建 checkpoint。
- 每个阶段可以生成 handoff summary。

---

# Phase 11：软件专用 Skills 落地

## 目标

为主流计算软件建立专用能力层。

## 开发内容

1. VASP skill：

```text
skills/simflow-vasp/
```

覆盖：
- POSCAR / INCAR / KPOINTS / POTCAR metadata
- OUTCAR / OSZICAR / vasprun.xml 解析
- 收敛性检查
- dry-run 检查

2. Quantum ESPRESSO skill：

```text
skills/simflow-qe/
```

覆盖：
- `pw.x` input
- 输出解析
- SCF 收敛检查

3. LAMMPS skill：

```text
skills/simflow-lammps/
```

覆盖：
- data file
- input script
- dump / log 解析
- RDF / MSD / diffusion 分析

4. Gaussian skill：

```text
skills/simflow-gaussian/
```

覆盖：
- `.com` 输入
- `.log` 解析
- 能量 / 频率 / 优化状态检查

## 交付物

```text
skills/simflow-vasp/
skills/simflow-qe/
skills/simflow-lammps/
skills/simflow-gaussian/
templates/vasp/
templates/qe/
templates/lammps/
templates/gaussian/
tests/fixtures/
docs/software-skills.md
```

## 验收标准

- 每个软件 skill 都能声明输入、输出、验证项。
- 每个软件 skill 都能接入 input_generation、compute、analysis 阶段。
- 每个软件 skill 都有示例 fixtures。
- 不要求第一版支持所有软件高级参数，但必须有扩展边界。

---

# Phase 12：DFT / AIMD / MD Dry-run 工作流落地

## 目标

完成三条端到端 dry-run workflow。

## 开发内容

1. DFT dry-run workflow：

```text
literature
-> review
-> proposal
-> modeling
-> input_generation
-> compute
-> analysis
-> visualization
-> writing
```

2. AIMD dry-run workflow：

```text
proposal
-> modeling
-> input_generation
-> compute
-> analysis
-> visualization
-> writing
```

3. MD dry-run workflow：

```text
proposal
-> modeling
-> input_generation
-> compute
-> analysis
-> visualization
-> writing
```

4. 每条 workflow 都需要：
   - 初始化 `.simflow/`
   - 生成 plan
   - 生成 artifact
   - 生成 checkpoint
   - 生成 verification report
   - 生成 handoff report

5. 所有 compute 默认 dry-run，不真实提交作业。

## 交付物

```text
workflow/workflows/dft.json
workflow/workflows/aimd.json
workflow/workflows/md.json
docs/examples/dft_workflow.md
docs/examples/aimd_workflow.md
docs/examples/md_workflow.md
tests/e2e/dft_dry_run*
tests/e2e/aimd_dry_run*
tests/e2e/md_dry_run*
```

## 验收标准

- DFT dry-run 可完整走通。
- AIMD dry-run 可完整走通。
- MD dry-run 可完整走通。
- 每条 workflow 至少生成：
  - workflow state
  - stage states
  - artifacts
  - checkpoints
  - reports
  - handoff

---

# Phase 13：外部系统集成增强

## 目标

在 dry-run 稳定后，逐步接入真实外部能力。

## 开发内容

1. 文献数据库真实连接：
   - arXiv
   - Crossref
   - Semantic Scholar
   - PubMed
   - ACS metadata 入口

2. 结构数据库真实连接：
   - Materials Project
   - COD
   - OQMD
   - ICSD adapter placeholder

3. HPC adapter 增强：
   - SLURM
   - PBS
   - LSF
   - 本地 shell
   - SSH
   - SFTP
   - tmux session tracking

4. 计算软件解析器增强：
   - VASP
   - QE
   - LAMMPS
   - Gaussian

5. 凭据管理规则：
   - 只从环境变量或用户配置读取
   - 不写入仓库
   - 不写入 artifact
   - 不进入日志

## 交付物

```text
mcp/servers/literature/connectors/
mcp/servers/structure/connectors/
mcp/servers/hpc/connectors/
mcp/servers/parsers/
docs/hpc-integration.md
docs/credentials-policy.md
tests/mcp/integration*
```

## 验收标准

- 没有凭据时系统仍能 dry-run。
- 有凭据时可以启用对应 connector。
- 真实 HPC submit 仍需 approval gate。
- 任何外部失败都能写入 report 和 checkpoint。

---

# Phase 14：测试体系与质量门落地

## 目标

建立覆盖插件、skills、workflow、MCP、runtime、schema、e2e 的测试体系。

## 开发内容

1. Skills 测试：

```text
tests/skills/
```

2. Workflow 测试：

```text
tests/workflow/
```

3. MCP 测试：

```text
tests/mcp/
```

4. Runtime 测试：

```text
tests/runtime/
```

5. Schema 测试：

```text
tests/schemas/
```

6. E2E 测试：

```text
tests/e2e/
```

7. Fixtures：

```text
tests/fixtures/
```

Fixtures 包含：
- CIF
- POSCAR
- OUTCAR
- OSZICAR
- vasprun.xml sample
- QE output sample
- LAMMPS log/dump sample
- Gaussian log sample

## 交付物

```text
tests/
scripts/validate_plugin.js
scripts/validate_skills.js
scripts/validate_schemas.js
docs/testing-strategy.md
```

## 验收标准

- 所有 schema 可校验。
- custom skill binding schema 可校验。
- 所有 skill 结构可校验。
- 所有 workflow 定义可校验。
- DFT / AIMD / MD dry-run e2e 可通过。
- 失败路径可测试，包括验证失败、artifact 缺失、checkpoint 恢复、HPC submit 被 gate 阻断。

---

# Phase 15：文档、示例与发布准备

## 目标

完成可交付版本的文档、示例和发布清单。

## 开发内容

1. 完成产品文档：

```text
docs/PRD.md
docs/technical-design.md
docs/workflow-layer-design.md
docs/skill-design.md
docs/mcp-design.md
docs/state-and-checkpoint.md
docs/artifact-schema.md
docs/verification-gates.md
docs/hpc-integration.md
docs/custom-skills.md
docs/user_guide.md
docs/developer_guide.md
```

2. 完成示例：

```text
docs/examples/dft_workflow.md
docs/examples/aimd_workflow.md
docs/examples/md_workflow.md
```

3. 完成插件发布说明：

```text
README.md
CHANGELOG.md
```

4. 完成开发维护脚本：

```text
scripts/scaffold_skill.js
scripts/scaffold_stage.js
scripts/validate_plugin.js
scripts/validate_skills.js
scripts/validate_schemas.js
```

## 交付物

```text
docs/
README.md
CHANGELOG.md
scripts/
```

## 验收标准

- 新开发者可以根据 developer guide 增加一个 stage 或 skill。
- 用户可以根据 user guide 启动 DFT / AIMD / MD dry-run。
- 文档明确哪些行为需要用户审批。
- 文档明确 SimFlow 不负责 LLM 实现。

---

# 版本里程碑

## v0.1.0：插件骨架版

完成：

```text
.codex-plugin/
AGENTS.md
skills 骨架
workflow 骨架
schemas 骨架
README
```

目标：SimFlow 可以作为插件结构被识别。

## v0.2.0：Workflow Layer 版

完成：

```text
workflow/stages
workflow/workflows
workflow/gates
workflow/policies
.simflow templates
state/artifact/checkpoint schemas
custom skill binding schema
```

目标：SimFlow 的阶段、状态、artifact 和 checkpoint 规则成型。

## v0.3.0：Skills 可用版

完成：

```text
workflow control skills
domain stage skills
agent role files
skill contracts
handoff skill
verification skill
```

目标：用户可以通过 skills 进入不同研究阶段。

## v0.4.0：MCP Dry-run 版

完成：

```text
simflow_state MCP
artifact_store MCP
checkpoint_store MCP
literature mock MCP
structure mock MCP
hpc dry-run MCP
parser mock MCP
```

目标：SimFlow 有稳定工具层，不依赖模型记忆维护状态。

## v0.5.0：DFT / AIMD / MD Dry-run 闭环版

完成：

```text
DFT dry-run e2e
AIMD dry-run e2e
MD dry-run e2e
artifact/checkpoint/report/handoff 全链路
```

目标：三类计算模拟 workflow 都能端到端跑通 dry-run。

## v0.6.0：外部系统 Adapter 版

完成：

```text
文献数据库 adapter
结构数据库 adapter
SLURM/PBS/LSF adapter
SSH/SFTP/tmux adapter
VASP/QE/LAMMPS/Gaussian parser 初版
```

目标：具备真实系统接入能力，但 submit 仍默认受审批控制。

## v1.0.0：稳定可交付版

完成：

```text
完整文档
完整测试
完整 dry-run
可选真实外部集成
稳定 checkpoint/recovery
稳定 artifact lineage
稳定 verification gates
```

目标：SimFlow 可以作为计算模拟研究 workflow layer 交付使用。

---

# 关键实施约束

1. SimFlow 不实现 LLM。
2. SimFlow 不以 CLI 作为主入口。
3. SimFlow 以 skills 作为用户入口。
4. SimFlow 使用 workflow layer 管理阶段、状态和规则。
5. SimFlow 使用 MCP 暴露稳定工具能力。
6. SimFlow 使用 `.simflow/` 保存项目状态、artifact、checkpoint、report 和日志。
7. 所有真实外部提交、凭据使用、高成本计算必须经过 approval gate。
8. Dry-run 必须优先于真实执行。
9. Artifact 必须版本化并记录 lineage。
10. 每个阶段必须支持独立进入、验证、恢复和 handoff。
11. SimFlow 不管理用户自定义 Codex skills 的存放、发现、安装、加载或执行。
12. 用户自定义 skill 可在无 binding 情况下由 SimFlow 根据 skill metadata 和用户请求轻量推断接入 workflow。
13. `.simflow/extensions/skills/*.json` 仅作为复杂或严格 workflow 场景的可选高级 binding 契约。
