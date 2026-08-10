---
name: simflow-qe
description: Reserved Quantum ESPRESSO placeholder; current SimFlow product does not support QE workflows.
---

## Cross-Session Experiment Memory

For work inside an existing user project, call `simflow_state/project_reentry` with the explicit canonical `project_root` before inspecting project files or performing work. Do not read or import host session transcripts as normal project memory. If the forward-only ledger has not started, call `begin_experiment` before new tracked work. Call `start_activity` before every project mutation, computation, analysis, transfer, or state change, and call `finish_activity` with outputs, outcome, failure/recovery details, and `next_action` afterward. Once the ledger is enabled, linked SimFlow writes must carry `session_context_id`, `experiment_id`, and `activity_id`. End with `session_handoff` when possible; an unclosed activity is intentionally surfaced as interrupted work on the next re-entry.

`.simflow/memory/ledger.sqlite3` is authoritative; JSON, JSONL, and Markdown files are derived views. Enabled-ledger writes fail closed in the core runtime, including direct runtime/helper calls. Propagate `SIMFLOW_SESSION_CONTEXT_ID`, `SIMFLOW_EXPERIMENT_ID`, optional `SIMFLOW_ITERATION_ID`, and `SIMFLOW_ACTIVITY_ID` to child processes. Treat the ledger as a human-readable electronic lab notebook backed by an immutable provenance DAG, not as a replacement for Git.

# SimFlow QE

## Trigger conditions

- This skill is a reserved placeholder. SimFlow does not currently provide a supported QE computation, analysis, or stage-runner path.
- If a user requests QE work, state that QE support is not available in the current product build and suggest using the generic SimFlow workflow layer to record user-provided files as open artifacts.
- Do not generate QE inputs, claim QE validation coverage, or route QE tasks through the canonical computation runner.

## Input conditions

- Record user-provided QE files as generic artifacts when the user explicitly asks for traceability.
- Preserve source, command, environment, and limitation notes in `.simflow/` metadata.
- Mark any interpretation as unsupported by SimFlow QE helpers unless the user supplies their own validated analysis.

## Output artifacts

- Generic user-provided file artifact metadata only.
- Optional limitation note or handoff note that states QE support is unavailable.
- No supported QE input manifest, validation report, parsed result, figure, or calculation claim.

## Status write rules

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- QE task label 只能作为用户提供 metadata/tag，不决定顶层 workflow。
- 不自动推进固定阶段；不得把 QE 映射到当前 VASP/CP2K/LAMMPS supported paths。

## Checkpoint rules

- checkpoint 记录 QE support unavailable、用户提供文件、缺失验证、下一步可选迁移路径。
- 不把未验证 QE 结果写成 SimFlow 已验证结果。

## Prohibited actions

- Do not claim supported QE input generation, validation, parsing, computation, or analysis.
- Do not default unknown QE tasks to SCF.
- Do not copy, redistribute, or expose pseudopotentials, licensed/proprietary files, credentials, or private paths.
- Do not submit real local, remote, or HPC jobs without the generic SimFlow approval gate.

## Manual confirmation scenarios

- The user needs QE-specific scientific advice, validation, or execution.
- The user wants unsupported QE outputs interpreted as final evidence.
- Any remote execution, licensed/proprietary data, credentials, or high-cost resource is involved.
