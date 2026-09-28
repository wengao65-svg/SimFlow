# SimFlow 精简重构方案（v2 Lite）

依据：`D:/sessions`（约 387 份 Codex rollout，其中约 84 个真实计算科研主会话）
与当前仓库 `1.4.0-dev` 代码对照。只分析、给方案，不在本文件内改代码。

---

## 1. 问题诊断（有会话证据）

### 1.1 用户已经说清楚的病根

2026-08-11 会话原话：

> SimFlow 现在真正的问题不是能力不够，而是把一些本来应该是内部约束的东西
> 做成了显式 Skill、显式 MCP 操作和显式目录结构，导致 Agent 每做一步都在
> 重复“加载规则—检查状态—登记—审批—再登记”。

同日另一条：

> 对于分析这个问题……`/mnt/d/REE/phase4_computation/stage1_force_field_validation/analysis`
> 就过于细化了，导致用户查看分析内容的时候非常麻烦。

2026-08-12 对 Experiment Notebook 的最大保留意见：

> 刚把旧 ledger 的大块复杂度清掉，紧接着又增加接近两千行 Experiment Memory /
> binding 逻辑。……`material_action` 已经越界。

### 1.2 量化：管理噪声远多于科学动作

全量扫描 `record` / `register` / evidence 类工具调用：

| 工具 | 次数 | 备注 |
| --- | ---: | --- |
| `record` | 512 | run 111 / analysis 102 / approval 60 / decision 60 / observation 58 / evidence_change 35 / attempt 35 / … |
| `register` | 296 | 大量失败 |
| `record_computation_evidence` | 169 | 大量被门禁拒绝 |
| `checkpoint` | 124 | |
| `read_state` | 118 | 多为满足前置条件而调 |
| `record_user_override` | 107 | |
| `record_analysis_evidence` | 44 | |
| `register_artifact` | 37 | |
| `record_stage_failure` | 13 | |

同一时期真正推进科研的用户指令，绝大多数是：

- “查看收敛 / 回传分析 / 画图对比”
- “从某 checkpoint 恢复 AIMD / MD”
- “准备输入 / 提交计算（需我确认）”
- “写大纲 / 写论文 / 提取文献数据”

**结论：登记与合规动作的调用量，已接近甚至超过科学动作本身。**

### 1.3 高频失败 = 仪式本身在制造摩擦

从工具返回里反复出现的错误：

1. `skill_engagement_contract_violation`  
   `Before calling register, you must call simflow_state/read_state first`
2. `Missing proposal artifacts: proposal.md, parameter_table.csv, research_questions.json`  
   —— 后续计算阶段被强制要求“提案三件套”，真实项目往往已有自己的方案文档。
3. `[Errno 21] Is a directory`  
   —— 把分析目录 / 数据目录当 artifact 文件登记，路径校验过严。
4. `No workflow state found`  
   —— 旧 workflow 状态机与新 compact store 并存，agent 不知该以谁为准。
5. POTCAR / transfer 早期被“合法用户也无法上传”策略卡死（后已修，但是  
   “内部约束做成显式闸门”的同一类问题）。

### 1.4 结构层面的过重

| 层 | 现状 | 判断 |
| --- | --- | --- |
| MCP 工具面 | 2 server / 8 tools，但历史会话仍打到 `register` / `read_state` / `record_*_evidence` 等旧名 | 兼容面 > 真实需要 |
| 记录本体 | 11 种 operational kind + 4 种 experiment entry + 多套 status 词表 | 分类学过细 |
| 哈希 | run_plan、artifact、evidence path、checkpoint input/restart、migration report 都要 hash | 只有执行边界与恢复边界需要 |
| `simflow_core` | 34 个模块，records/state/repair/verification/status/proposals… | 内部约束泄漏成公共语义 |
| Domain Skills | gpumd 115KB / reference-extraction 120KB / analysis 102KB / vasp 92KB | 指南已膨胀成“第二套 runtime 文档” |
| `workflow/` | 39 个 policy/gate/recipe JSON | 状态机与门禁剧本过多 |
| 目录 | 六 phase 模板 + analysis 归属规则 | 被执行成强制布局 |

---

## 2. 设计原则（重构后必须成立）

1. **SimFlow 是实验笔记本 + 执行安全带，不是 workflow OS。**
2. **内部约束不得要求 agent 显式调用。** 能在 write 时静默校验的，绝不加前置工具。
3. **一次科研动作，最多一次记录。** 读、想、画图、改脚本默认零写入。
4. **哈希只出现在两处：** 真实执行的 `run_plan_hash`；恢复点的输入/重启文件指纹。
5. **科学事实住在项目文件里；** 笔记本只写“问了什么、试了什么、看到什么、决定什么”。
6. **尊重既有目录与用户提交脚本。** 不重写、不强制 phase、不把 analysis 拆到过细子目录。
7. **Taxonomy 封顶且扁平。** 不再为新概念加 entry type / record kind。

---

## 3. 目标形态

```text
.simflow/
├── notebook.md          # 人可读实验笔记本（追加）
├── journal.jsonl        # 仅安全/执行事实（追加，极少量）
└── checkpoints/         # 可选；仅长任务/可恢复边界
    └── <id>.json
```

对比现状：去掉 `project.json` 派生摘要的“必读”地位、去掉 `experiments/` 多文件索引、
去掉 `reports/` 自动报告流水、去掉 legacy migration 确认仪式（旧数据只读不迁）。

### 3.1 `notebook.md`：科研语义的唯一载体

每条 entry 只有 4 类（保持 v1.1.1 已收紧的 ontology，不再加）：

| entry | 含义 | 何时写 |
| --- | --- | --- |
| `question` | 科学问题 / 假设 | 开一个 Experiment 时一次 |
| `try` | 一次科学尝试（参数组、方法、模型版本） | 换策略时 |
| `see` | 观察到的结果与不确定性 | 有实质结果时 |
| `decide` | 下一步决定 / 放弃 / 收敛 | 分支点 |

写入格式保持 Markdown 可读，机器元数据用一行 HTML 注释即可：

```markdown
## 2026-08-10 · try · NEPv3 筛选后重标 DFT
<!-- simflow: {"id":"try_20260810a","exp":"exp_lbs_relabel"} -->
- 策略：NepTrainKit 筛选 → VASP single-point 重标
- 输入：`NEP_Baseline_.../LBS_2346_MERGED_POOL/*_good_model`
- 状态：输入模板已定，等待 8163 资源
```

**不再写：** artifact 注册表、sha256 清单、stage 状态机、approval 流水、
material_action 生命周期、helper_evidence 全字段。

### 3.2 `journal.jsonl`：只记“有后果的事实”

允许的 `kind` 收缩为 5 个：

```text
approval   绑定 run_plan_hash 的真实执行批准
run        提交 / 完成 / 失败（含 scheduler id）
failure    需要跨会话记住的失败边界
change     对持久证据的删除/覆盖/替换等不可逆操作（原 evidence_change）
recovery   恢复点创建或使用
```

其余（milestone / artifact / analysis / note / migration / attempt / decision…）
**全部禁止写入 journal**——它们要么进 notebook，要么根本不需要记。

### 3.3 `checkpoints/`：恢复指针，不是状态快照

字段封顶：

```json
{
  "id": "ckpt_lbs_md_20260815",
  "what": "NEPv5 3000K NPT 熔融淬火 · La 10H2O",
  "inputs": [{"path": "...", "sha256": "..."}],
  "resume": "bash run_npt_resume.sh",
  "risk": "水分子重连失败时勿直接续跑"
}
```

没有 record_id 链、没有 records byte offset、没有 lineage 图。

### 3.4 MCP 面：6 个工具，不再是 8+

| 工具 | 职责 | 变化 |
| --- | --- | --- |
| `recall` | 读项目记忆（合并 inspect + read_state） | 替代 inspect |
| `note` | 写一条 notebook entry | 替代 record(channel=experiment) |
| `log` | 写一条 journal 事实 | 替代 record(operational) + 各类 evidence |
| `mark` | 建/用恢复点 | 合并 checkpoint + recover |
| `plan` | 不变（hpc） | 保留 run_plan_hash |
| `transfer` / `submit` / `status` | 不变（hpc） | 自动写 journal 的 `run` |

**删除：** `register`、`register_artifact`、`record_computation_evidence`、
`record_analysis_evidence`、`record_user_override`、`record_stage_failure`、
`read_state`、`init_workflow`、`workflow_status`、`update_stage`、
`stage_readiness`、`project_readiness`、`create_goal`…（历史兼容名不再暴露）。

**删除所有 engagement contract：** 不再要求“先 read_state 再 register”，
不再要求“先有 proposal 三件套才能记证据”。写入时静默清洗密钥即可。

### 3.5 哈希策略：只守两道门

| 保留 | 去掉 |
| --- | --- |
| `run_plan_hash`（脚本+输入+目标机+资源+传输/破坏范围） | artifact 登记 hash |
| checkpoint 内输入/重启文件 sha256 | evidence path 全量 hash |
| | migration report hash 确认仪式 |
| | notebook entry hash |
| | project.json 派生一致性 hash |

审批仍绑定 `run_plan_hash`：不变可复用，一变即失效。这是全系统唯一强制哈希。

### 3.6 Skills：指南瘦身

- **Task / Domain Skills 保持纯指导**，删除 SKILL.md 中的  
  “State Machine / Required Evidence / Submit-Readiness Contract /  
  artifact / checkpoint / handoff 写入” 等 runtime 章节。
- Domain skill 体积目标：每个 ≤ 40KB（references 可另放，但不进主文件）。
- analysis 归属一句话规则：**跟数据走**。  
  单次计算的图放该计算目录；跨 run 对比放最近公共父目录；  
  全文级综合才进 `phase5_analysis_visualization/`（若存在）。  
  **禁止** 为每个微单元强制建 `analysis/`。
- 提交脚本：**用户脚本正确则原样用**；最多提示 diff，不自动重写。

### 3.7 目录与迁移

- 六 phase 只出现在“新项目建议”一段话里，runtime 零强制。
- 旧 `.simflow/state`、`.simflow/memory`、嵌套 `.simflow`：**只读、不迁、不建报告**。  
  `recall` 能看见就显示“legacy，未纳入新账本”。
- 删除 migration 确认哈希流程（为它写的代码与测试一并退役）。

---

## 4. 迁移映射（旧 → 新）

| 旧概念 | 新去向 |
| --- | --- |
| Experiment / Attempt / Observation / Decision | notebook `question` / `try` / `see` / `decide` |
| `evidence_change` | journal `change` |
| `approval` / `run` / `failure` / `checkpoint` / `recovery` | journal 同名或 `mark` |
| `milestone` / `artifact` / `analysis` / `note` / `migration` | 不记；写进 notebook 正文或项目 README |
| `material_action` / recovery entry | 已在 v1.1.1 删除，保持删除 |
| helper_evidence schema 全字段 | helper 返回 stdout/JSON 给 agent；需要留痕时写一条 `see` |
| `project.json` / `experiments/index.md` | 删除或改为 `notebook.md` 自身目录 |
| proposal 三件套门禁 | 删除；方案文档由用户项目自管 |
| skill engagement contract | 删除 |

---

## 5. 实施切片（按 PR，可独立合并）

### PR-1 冻结与删除门禁（立刻减痛）
- 删除 engagement contract、proposal-artifact 门禁、register 前置 read_state。
- 现有测试改为“写入成功 + 密钥清洗”断言。
- **验收：** 真实项目里连续 prepare→submit 不再出现上述 1.3 的 5 类错误。

### PR-2 MCP 面收敛
- 暴露 `recall` / `note` / `log` / `mark`；旧名映射到新语义或直接 404 并提示。
- **验收：** `list_tools` ≤ 8；一次 MD 启动全流程工具调用 ≤ 6（含 hpc）。

### PR-3 存储合并
- `notebook.md` + `journal.jsonl` + `checkpoints/` 落地；  
  writer 只写新格式；reader 兼读旧 `experiments/*.md` 与 `records.jsonl` 一次展开。
- journal kind 封顶 5；非法 kind 直接拒绝。
- **验收：** `.simflow` 目录项 ≤ 3；单条 entry 无 hash 字段（checkpoint 除外）。

### PR-4 哈希与恢复瘦身
- 去掉 artifact/evidence/migration 哈希；checkpoint 字段封顶。
- `recover` → `mark --use`，只校验路径存在 + 输入 hash 匹配。
- **验收：** 全库 `sha256`/`hashlib` 触点下降 ≥ 60%，且 hpc plan/approval 测试全绿。

### PR-5 Skills 与 workflow 剧本瘦身
- SKILL.md 去 runtime 章节；`workflow/` policy 从 39 收到 ≤ 10（只留 dry-run、审批、凭证、POTCAR、恢复、分析归属）。
- **验收：** `npm run validate:all` + `pytest`；单 skill 主文件 ≤ 40KB。

### PR-6 文档与示例对齐
- README / AGENTS / user_guide 重写为“笔记本 + 安全带”叙事。
- 示例项目展示：零强制目录、用户脚本原样提交、analysis 跟数据走。
- **验收：** 新用户 10 分钟内完成 recall→note→plan→submit（dry-run）闭环。

---

## 6. 明确不做

- 不恢复 SQLite / session ledger / activity controller。
- 不新增 public Skill、不新增 MCP server。
- 不做 SimFlow 自己的 LLM / workflow 执行器。
- 不自动迁移、不重命名用户科学文件。
- 不把 notebook 变成“实验版 git”。

---

## 7. 成功指标（用 sessions 同口径回放）

| 指标 | 现状（抽样） | 目标 |
| --- | --- |:---: |
| 每个用户科学指令的 SimFlow 写入次数 | 常见 3–8 | ≤ 1 |
| 登记/合规类工具调用占全部 SimFlow 调用比 | ~50%+ | ≤ 15% |
| 因门禁/契约导致的失败调用 | 常见 top 错误 | ≈ 0 |
| `.simflow` 目录项 | 5+ 子树 | ≤ 3 |
| 对外可见 kind/entry 词表 | 15+ | 9（5 journal + 4 notebook） |
| 用户脚本被重写次数 | 会话中有明确抱怨 | 0（仅建议 diff） |

---

## 8. 一句话

**把 SimFlow 从“每步都要登记的项目管理系统”，收成“一本实验笔记 + 一条执行安全带”。**
内部约束静默生效，显式接口只保留科研记忆与真实执行审批。
