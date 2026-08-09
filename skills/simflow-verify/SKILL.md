---
name: simflow-verify
description: Verify workflow state, artifacts, and readiness checks in SimFlow.
---

## Cross-Session Experiment Memory

For work inside an existing user project, call `simflow_state/project_reentry` with the explicit canonical `project_root` before inspecting project files or performing work. Do not read or import host session transcripts as normal project memory. If the forward-only ledger has not started, call `begin_experiment` before new tracked work. Call `start_activity` before every project mutation, computation, analysis, transfer, or state change, and call `finish_activity` with outputs, outcome, failure/recovery details, and `next_action` afterward. Once the ledger is enabled, linked SimFlow writes must carry `session_context_id`, `experiment_id`, and `activity_id`. End with `session_handoff` when possible; an unclosed activity is intentionally surfaced as interrupted work on the next re-entry.

# SimFlow Verify — 统一验证 Skill

## 触发条件

- 阶段完成需要验证
- 用户请求验证某个 artifact
- 工作流推进需要通过验证门

## 输入条件

- 验证目标：stage 名称或 artifact 路径（必需）
- 验证依据：stage intent、evidence_outputs、artifact metadata、lineage、checkpoint、gate evidence 或用户指定检查
- 可使用 readiness diagnostics、runtime helper、用户提供脚本或第三方科学库，但必须记录 evidence

## 输出 Artifact

- verification/readiness report artifact，可按需要输出为 JSON、Markdown 或 structured result
- 每项检查必须区分直接 evidence、helper 输出和 agent interpretation

## 状态写入规则

- 只在显式 `project_root` 下更新 `.simflow/state/verification.json` 或 `.simflow/reports/`
- read-only readiness 查询不得修改 artifact 内容
- 不要从 plugin root、MCP cwd 或 `.omx/` 推断 workflow state

## Checkpoint 规则

- 验证失败时创建 failure checkpoint
- 阶段边界验证通过时可引用最近 checkpoint 或创建新的 boundary checkpoint

## 禁止事项

- 不要跳过验证项
- 不要修改被验证的 artifact
- 不要在验证失败时继续推进
- 不要要求固定 validator、固定 parser 或固定 report 文件名
- 不要把 warning 或 missing evidence 解释成 pass

## 需要人工确认的场景

- 验证结果为 warning 时
- 验证规则不明确时
- 验证会触发真实执行、远程访问、destructive operation 或 licensed/proprietary file handling 时

## Directory Hygiene Checks

When verifying a project, the host agent should perform the following
text-level directory hygiene checks against the contract defined in
`docs/user-project-layout.md`. These are advisory checks reported in the
verification output; they do not block stage transitions unless the user
or the gate explicitly requires a clean layout.

1. **Root allowlist check.** Confirm the project root contains only:
   `README.md`, `workflow.md`, `.gitignore`, `.git/`, `.simflow/`, the six
   `phaseN_*` directories (only those in active use), and the nine shared
   directories (`scripts/`, `reference/`, `config/`, `templates/`,
   `tests/`, `docs/`, `archives/`, `legacy/`, `scratch/`). Flag any other
   top-level entry — for example `POTCAR.*`, `*.tar.gz`, `*.zip`, `*.pb`,
   `*.xyz` bulk structures, `train.pid`, `*.py`, `*.sh`, `*.log`,
   `*.tsv`, `*.bak.*`, `driver.*`, `submit_*.{sh,log}`,
   `*_hpc_submit_plan_*.md`, `workflow.md.bak_*`.

2. **Top-level `stageN_*` prohibition.** Flag any `stageN_*` directory
   sitting directly at the project root. Such directories must live inside
   a `phaseN_*` parent. (Counter-example: a root-level `stage3_aimd/` is a
   violation; it should be `phase4_computation/stage3_aimd/`.)

3. **Top-level descriptive-experiment prohibition.** Flag any top-level
   directory whose name is not in the phase allowlist or the shared
   allowlist. (Counter-examples: root-level `NEP_Training_*`,
   `DFT_DataSets_*`, `MD_Test_*`, `vasp_label_jobs_*` are violations;
   they belong under `phase4_computation/stageN_*/`.)

4. **No nested `.simflow/`.** Flag any `.simflow/` directory found inside
   a `phaseN_*/stageN_*/` subtree. `.simflow/` may exist only at
   `project_root`. (Counter-example: `phase4_computation/stageN_*/.simflow/`
   is a violation.)

5. **Analysis placement check.** Flag any `_analysis`-suffixed sibling
   directory next to its source stage. Single-stage analysis must nest as
   `<stage>/analysis/`, not sit as `<stage>_analysis/`. Cross-stage
   analysis belongs under `phase5_analysis_visualization/stageN_<topic>/`.
   (Counter-example: `stage3_aimd_analysis/` next to `stage3_aimd/` is a
   violation.)

6. **Prep/run prefix overload check.** Flag any directory pair that uses
   the same prefix for both dataset-prep and run, distinguishing only by
   a `_Training` suffix or no suffix at all. Prep and run must be
   separated as `dataset_prep/` vs `run_step1/` / `run_step2/` inside a
   single stage directory. (Counter-example: `NEP_Training_LBS_Transport_DFT_2050/`
   prep next to `NEP_Training_LBS_Transport_DFT_2050_Training/` run is a
   violation.)

7. **`.simflow/artifacts/` stage-name allowlist.** Flag any
   `.simflow/artifacts/<name>/` directory whose `<name>` is not in
   {`literature_review`, `proposal`, `modeling`, `computation`,
   `analysis_visualization`, `writing`, `figures`, `security`}.
   Specifically flag the non-canonical duplicates `compute/`,
   `analysis/`, `literature/`, `models/`.

8. **Scattered gate markers.** Flag any `APPROVE_*` file found inside a
   `phaseN_*/stageN_*/` tree. Gate decisions belong in
   `.simflow/state/gates.json`.

9. **Bare-integer iteration check.** Flag any directory whose name is
   a bare integer (e.g. `2050`, `2100`, `2120`) that does not carry a
   description or date. Iteration should be encoded as
   `vN_<desc>_<YYYYMMDD>/`.

10. **Tests duplication check.** Flag `test_*.py` files found under
    `scripts/`. `tests/` is the single test location.

Reporting: list each violation with its path and the rule number it
violates. Do not auto-fix; report for the host agent and user to resolve.
