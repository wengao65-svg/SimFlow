---
name: simflow-writing
description: Write evidence-traceable SimFlow deliverables and computational simulation manuscripts from registered artifacts, figures, analysis outputs, literature, and user drafts.
---

# SimFlow Writing

`simflow-writing` is the writing-stage skill for traceable scientific deliverables. It can also help plan, structure, draft, revise, and review computational materials or physics manuscripts involving DFT, AIMD, classical MD, machine-learning potentials, active learning, uncertainty, diffusion, phase transitions, transport, interfaces, and related simulations.

## 触发条件

- 用户请求论文草稿、综述、proposal、组会材料、README、内部报告、方法说明、figure captions、cover letter、reviewer response 或其他科研文本。
- 用户请求 Nature/PR/npj-style manuscript planning, abstracts, introductions, results, discussions, methods, figure plans, captions, conclusions, or manuscript review in English or Chinese.
- 当前任务需要把文献、模型、计算、分析、图表或用户输入转化为可审查文字。
- 用户需要判断论文应 framed as a method, physical-problem, scale-breakthrough, reliability/statistics, or hybrid contribution.
- 用户可以从 writing 阶段直接进入，只要输入证据足够。

## 输入条件

- 可用的 literature、proposal、modeling、computation、analysis、figure 或 user-provided artifacts。
- 可选：目标读者、期刊/会议、格式、语气、长度、引用风格、章节结构、用户草稿、figure storyboard、claim map 或 reviewer comments。
- 不要求固定文档结构、固定文件名、固定模板或所有阶段都已完成。
- 写作任务开始前应明确 manuscript type、one-sentence contribution、核心 claim、figure/data evidence chain、缺失证据和结论强度。

## 输出 Artifact

- 用户指定格式的草稿、报告、说明、caption、slide text、proposal、review、cover letter、response letter 或其他写作产物。
- Claim map、citation map、figure/data/script references、manuscript outline、figure storyboard、review checklist 或其他 evidence traceability 记录。
- 未完成计算、未验证分析和 speculative 解释必须在文本中标记。
- 对外可交付文本应区分 source claim、agent interpretation、user-provided fact、calculation result、analysis result 和 speculation。

## 状态写入规则

- 写入 `.simflow/` 前必须显式解析 `project_root`。
- 关键科学 claim 必须链接到文献、模型、计算、分析、图表或用户输入 artifact。
- 引用、直接 quote、source claim、agent interpretation 和 speculation 应分开处理。
- 写入报告、草稿、claim map、figure plan、caption、review 或 handoff material 时，注册 artifact metadata、source paths、parameters、assumptions、lineage 和 missing evidence。
- SimFlow writing 是 workflow layer activity，不替代作者的科学判断、期刊策略或真实 peer-review。

## Core Workflow

1. Identify the manuscript type: method, physical-problem, scale-breakthrough, reliability/statistics, or deliberate hybrid.
2. State the one-sentence contribution in the form: "We show/introduce X, which enables Y by overcoming Z."
3. Build the figure storyboard and rough analysis plots before drafting polished prose.
4. Separate method validation from physical discovery; make clear which figures establish trust and which deliver new science.
5. Draft in the target journal style, with claims calibrated to evidence strength.
6. Review for common computational-paper weaknesses: weak baseline, insufficient sampling, missing uncertainty, unclear DFT settings, unstable MD validation, or overclaiming transferability.

## Reference Selection

Load only the reference needed for the current writing task:

- `references/method-paper.md`: new MLP, training workflow, sampling protocol, active learning, pretraining, foundation potential, uncertainty, or general-purpose potential papers.
- `references/physical-problem-paper.md`: manuscripts whose main claim resolves a materials or physics question.
- `references/scale-breakthrough-paper.md`: novelty from larger scale, longer times, or more realistic thermodynamic or chemical conditions than DFT/AIMD can reach.
- `references/reliability-statistics-paper.md`: AIMD/MD statistical error, sampling adequacy, uncertainty, confidence, reproducibility, or reliability criteria.
- `references/section-templates.md`: section-level manuscript structure.
- `references/abstracts.md`: abstract drafting or revision.
- `references/introductions.md`: introduction drafting or revision.
- `references/results.md`: Results drafting from processed data, figures, and rough plots.
- `references/discussions.md`: Discussion or Conclusion drafting.
- `references/methods.md`: Methods drafting or reproducibility checks.
- `references/figure-captions.md`: figure caption writing.
- `references/reviewer-checklist.md`: final manuscript checking before handoff or submission.

For hybrid manuscripts, load the primary type reference first, then only the section reference needed for the current task.

## Writing Rules

- Prefer figure-first planning. For each claim, ask which figure proves it.
- Make the first paragraph about the scientific bottleneck, not about the software or model name.
- Do not let "DFT accuracy with MD efficiency" be the whole novelty; specify what capability, regime, or conclusion becomes possible.
- Treat energy/force/stress error as necessary but insufficient. Require MD stability and physically meaningful property validation.
- Distinguish in-distribution accuracy, interpolation, extrapolation, and downstream transfer.
- For trajectory-derived quantities, check finite-size effects, finite-time effects, independent trajectories/seeds, and uncertainty estimates.
- Name the reference standard precisely: DFT functional, dispersion, Hubbard U, pseudopotential, cutoff, k-point scheme, thermostat/barostat, timestep, ensemble, cell size, trajectory length, number of seeds, and uncertainty method when relevant.
- When the user provides local reference papers, use them as style and structure examples, but do not overfit wording.

## Default Output Shapes

- For planning or discussion: manuscript type, one-sentence contribution, 5-6 figure plan, section outline, key validation requirements, and likely reviewer concerns.
- For drafting: polished scientific prose in the requested language, with placeholders only where data are missing, plus the missing data needed to remove placeholders.
- For revision: preserve the scientific claim unless asked to change it; improve logic, specificity, transitions, and claim calibration.
- For review: lead with evidence gaps, overclaims, missing controls, missing uncertainty, reproducibility issues, and section-level fixes.

## Optional helper scripts

- `scripts/run_writing_stage.py`: Generate canonical writing-stage methods, results, claim map, reproducibility package, and handoff records from SimFlow workflow state.
- `scripts/build_reproducibility_package.py`: Build reproducibility package outputs from registered writing and upstream artifacts.

These helpers are optional. Writing deliverables may also be produced by direct agent drafting, user-provided templates, notebooks, scripts, or external tools when evidence, lineage, assumptions, and missing data are recorded.

## Checkpoint 规则

- 草稿可审查、可交接、可提交给用户或发现证据缺口时创建 checkpoint。
- checkpoint 记录当前写作产物、证据覆盖、缺失 claim、未解决风险和下一步。
- 不把未完成、未验证或 speculative 的分析写作 checkpoint 成最终结论。

## 禁止事项

- 不要编造文献、citation、数据、图表、计算结果、收敛状态或实验事实。
- 不要把未完成计算、dry-run、计划任务或失败任务写成已完成结果。
- 不要强制生成某个固定报告文件、固定章节结构、固定 handoff 文件名或固定期刊叙事。
- 不要用泛化 novelty 替代可验证贡献；不要过度声称 transferability、accuracy、scale、mechanism 或 causal conclusion。
- 不要把 source wording 长段复制进输出；必要 direct quote 应保持短句并标注来源。

## 需要人工确认的场景

- 文本目标、受众、格式、引用风格、目标期刊、语言、篇幅或结论强度不明确。
- 关键 claim 缺少证据、证据相互矛盾或只有 speculative 支持。
- 用户要求超出当前 artifact 能支持的科学结论。
- 论文类型、figure logic、baseline、uncertainty standard、reference method 或 reviewer response strategy 会 materially affect scientific claims.
