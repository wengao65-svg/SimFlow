# Approval Reviewer SimFlow Discipline Contract

## Purpose

This document defines what SimFlow state-consistency signals an approval
reviewer (Codex guardian / Claude Code reviewer) should check when
evaluating agent actions in projects that use SimFlow.

## Problem

The deep audit of PEE_NEP and Li-O-B-Si projects revealed that approval
reviewers (Codex's guardian subagent) systematically approved cargo-cult
patterns — agents loading 243 SimFlow skill files but calling 0 MCP tools,
while running compute and building ad-hoc TSV state files. The reviewer
only evaluated compute risk (GPUMD binary, SSH, file writes) and never
flagged workflow discipline violations.

## Signals to Check

### 1. Skill-Load vs MCP-Call Gap (Cargo-Cult Detection)

**Signal**: Agent loaded SimFlow SKILL.md files (via `sed`/`exec_command`)
but did not call any SimFlow MCP tools (`simflow_state/*`, `artifact_store/*`,
`checkpoint_store/*`).

**Action**: Flag as `workflow_discipline_warning` in the reviewer rationale.
The agent is treating SimFlow skills as documentation rather than workflow
contracts.

**Detection**: Check if the transcript contains `SKILL.md` reads but no
`mcp__simflow_state` / `mcp__artifact_store` / `mcp__checkpoint_store` calls.

### 2. State-Write Without State-Read

**Signal**: Agent called `artifact_store/register` or
`checkpoint_store/create` without first calling `simflow_state/read_state`
in the same session.

**Action**: This is now hard-blocked by the engagement contract (P0.7).
If the reviewer sees a `skill_engagement_contract_violation` error in the
transcript, it means the agent tried to write state without reading first.

### 3. Unregistered Compute Directories

**Signal**: The project contains directories with compute marker files
(`train.log`, `slurm-*.out`, `OUTCAR`, `nep.in`, `run.in`) that are not
referenced in `jobs.json` or `artifacts.json`.

**Action**: Recommend running `simflow_state/orphan_compute_scanner` to
identify unregistered compute. Flag if the agent ran compute without
registering it.

### 4. Risky Directory Names

**Signal**: Project contains directories with names containing `NoGate`,
`Relaxed`, `Bypass`, `SkipGate`.

**Action**: Flag as `gate_bypass_suspected`. Recommend recording the
override via `simflow_state/record_user_override` if the bypass was
intentional.

### 5. Stale State Timestamps

**Signal**: `workflow.json.updated_at` is more than 24 hours behind the
latest checkpoint's `created_at`.

**Action**: Flag as `state_staleness_warning`. The workflow state may not
reflect recent work. Recommend running `simflow_state/repair_state`
(Phase 5) to refresh.

### 6. Missing Stage Declarations

**Signal**: Checkpoints reference `stage_id`s that are not in `stages.json`.

**Action**: This is now prevented by P1.4 (stage_id validation). If
historical checkpoints have this issue, recommend running `repair_state`.

## Implementation Status

- **P0.7 (engagement contract)**: Implemented — hard-blocks state-write
  without prior read_state
- **P2.1 (orphan_compute_scanner)**: Implemented — scans for unregistered
  compute
- **P2.3 (record_user_override)**: Implemented — records gate bypasses
- **P2.4 (gate_decision_id enforcement)**: Implemented — blocks job records
  without gate approval
- **repair_state (Phase 5)**: Implemented — read-only audit plus backed-up,
  confidence-gated structural repair
- **P7.3 host adaptation**: Implemented through MCP `clientInfo`; invocation
  guidance adapts without requiring skill-load telemetry
- **Signal 1 (cargo-cult detection)**: Not yet automated — requires Codex/
  Claude Code platform to expose skill-load events to SimFlow
- **Signal 3-6**: Detectable via existing SimFlow tools but not yet
  integrated into reviewer workflow

## Platform Telemetry Boundary

SimFlow does not require Codex/Claude Code skill-load hooks. MCP `clientInfo`
supports host-specific discovery guidance, while the engagement contract
enforces state discipline. Direct skill-load counting remains unavailable
unless a host explicitly exposes that telemetry in the future.

## Reviewer Rationale Template

When reviewing actions in a SimFlow project, the reviewer should include:

```json
{
  "simflow_discipline": {
    "skills_loaded": <count>,
    "mcp_tools_called": <count>,
    "cargo_cult_detected": <bool>,
    "state_written": <bool>,
    "state_read_first": <bool>,
    "compute_registered": <bool|null>,
    "risky_dirs_detected": <bool>,
    "warnings": ["..."]
  }
}
```

The rationale shape remains reviewer guidance. Structural signals are available
through SimFlow state tools; direct skill-load counts remain host-dependent.
