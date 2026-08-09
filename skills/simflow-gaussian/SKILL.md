---
name: simflow-gaussian
description: Reserved Gaussian placeholder; current SimFlow product does not support Gaussian workflows.
---

## Cross-Session Experiment Memory

For work inside an existing user project, call `simflow_state/project_reentry` with the explicit canonical `project_root` before inspecting project files or performing work. Do not read or import host session transcripts as normal project memory. If the forward-only ledger has not started, call `begin_experiment` before new tracked work. Call `start_activity` before every project mutation, computation, analysis, transfer, or state change, and call `finish_activity` with outputs, outcome, failure/recovery details, and `next_action` afterward. Once the ledger is enabled, linked SimFlow writes must carry `session_context_id`, `experiment_id`, and `activity_id`. End with `session_handoff` when possible; an unclosed activity is intentionally surfaced as interrupted work on the next re-entry.

# SimFlow Gaussian

## Trigger conditions

- This skill is a reserved placeholder. SimFlow does not currently provide a supported Gaussian computation, analysis, or stage-runner path.
- If a user requests Gaussian work, state that Gaussian support is not available in the current product build and suggest using generic SimFlow artifact tracking for user-provided files.
- Do not generate Gaussian inputs, claim Gaussian validation coverage, or route Gaussian tasks through the canonical computation runner.

## Input conditions

- Record user-provided Gaussian files as generic artifacts when the user explicitly asks for traceability.
- Preserve source, command, environment, charge/multiplicity assumptions, and limitation notes in `.simflow/` metadata.
- Mark any interpretation as unsupported by SimFlow Gaussian helpers unless the user supplies their own validated analysis.

## Output artifacts

- Generic user-provided file artifact metadata only.
- Optional limitation note or handoff note that states Gaussian support is unavailable.
- No supported Gaussian input manifest, validation report, parsed result, figure, or calculation claim.

## Status write rules

- 写入 `.simflow/` 前必须显式传入 `project_root`。
- Gaussian task label 只能作为用户提供 metadata/tag，不决定顶层 workflow。
- 不自动推进固定阶段；不得把 Gaussian 映射到当前 VASP/CP2K/LAMMPS supported paths。

## Checkpoint rules

- checkpoint 记录 Gaussian support unavailable、用户提供文件、缺失验证、下一步可选迁移路径。
- 不把未验证 Gaussian 结果写成 SimFlow 已验证结果。

## Prohibited actions

- Do not claim supported Gaussian input generation, validation, parsing, computation, or analysis.
- Do not default unknown Gaussian tasks to optimization, static, or frequency.
- Do not hide unconverged optimization, imaginary frequency risk, inconsistent charge/multiplicity, or missing evidence.
- Do not save credentials, disclose licensed/proprietary files, or submit real local, remote, or HPC jobs without the generic approval gate.

## Manual confirmation scenarios

- The user needs Gaussian-specific scientific advice, validation, or execution.
- The user wants unsupported Gaussian outputs interpreted as final evidence.
- Any remote execution, licensed/proprietary data, credentials, or high-cost resource is involved.
