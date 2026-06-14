# Release Smoke Results

Use this file as the local release record before publishing a version. Replace
the unchecked boxes with results from the candidate commit. Do not record
credentials, hostnames that should remain private, or proprietary file content.

## Candidate

- Version: 0.8.12
- Source candidate commit: `9e88475fde70f870479f5574e892e7a0fefcf3ba`
- Codex marketplace candidate commit: `237d3bfa2f05bb3cd037b63f48961bdcd5b5f087`
- Claude marketplace candidate commit: `a1210bb15ac183326fc18f5f3581a8ea8f04cc3d`
- Date: 2026-06-14
- Operator: Codex validation with completed three-branch atomic remote push over `ssh.github.com:443`

## Automated Gates

- [x] `git status --short --branch` clean at published candidate
- [x] `python -m pytest tests/ -q`: 592 passed, 7 skipped
- [x] `python scripts/audit_skill_scripts.py`: all helper contracts OK
- [x] `npm run validate:release`: 0 errors
- [x] `npm run build:codex-marketplace`
- [x] `SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin`: 0 errors
- [x] `npm run build:claude-marketplace`
- [x] `SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin`: 0 errors
- [x] Codex marketplace branch includes `simflow-gpumd` and `simflow-mlp`
- [x] Claude marketplace branch includes `simflow-gpumd` and `simflow-mlp`
- [x] Post-push `git ls-remote` matched all three target refs

## Post-0.8.12 Development Validation Snapshot

This snapshot records source-tree validation after the generic MLP-MD evidence
and recovery hardening work. It is not a manual marketplace install smoke and
does not replace the unchecked host-level install items below.

- Source commit: `9e88475 Include GPUMD and MLP skills in marketplace wrappers`
- Date: 2026-06-14
- `git status --short --branch`: clean
- `python -m pytest tests/ -q`: 592 passed, 7 skipped
- `python scripts/audit_skill_scripts.py`: all helper contracts OK
- `npm run validate:release`: 0 errors

## Post-Push Safety Hardening Snapshot

This snapshot records the follow-up `hpc.submit` stale-approval audit. It is a
source-tree hardening check and has not yet been published to the marketplace
branches.

- Date: 2026-06-14
- `python -m pytest tests/e2e/test_submit_safety_acceptance.py tests/mcp/test_hpc_server.py tests/mcp/test_slurm_connector.py -q`: 33 passed
- `python -m pytest tests/ -q`: 594 passed, 7 skipped
- Added requirement: an approved `hpc_submit` gate decision must bind
  `dry_run_evidence`, `script_hash`, and `input_artifact_hash`; stale or
  unbound approvals must not authorize real submit.

## Codex Install Smoke

- [ ] `codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace`
- [x] Isolated local-wrapper marketplace add succeeds from `dist/codex-marketplace`
- [x] Isolated local-wrapper install succeeds for `simflow@simflow-marketplace`
- [x] Installed plugin cache contains `simflow`, `simflow-vasp`, `simflow-gpumd`, and `simflow-mlp`
- [x] Installed plugin cache exposes all seven SimFlow MCP server configs
- [x] Installed hpc server blocks submit without required project/gate evidence
- [ ] Interactive `$simflow`, `$simflow-vasp`, `$simflow-gpumd`, and `$simflow-mlp` routing verified in a live Codex session
- [x] Real submit remains blocked without dry-run evidence, matching hashes,
      credential scan, and explicit approval

Notes:

```text
2026-06-14: Remote GitHub marketplace add was attempted in an isolated
/tmp HOME/CODEX_HOME but did not return after more than 90 seconds and was
terminated. Local wrapper marketplace add/install succeeded from
dist/codex-marketplace in an isolated /tmp HOME/CODEX_HOME.
```

## Claude Code Install Smoke

- [ ] `claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace`
- [x] Isolated local-wrapper marketplace add succeeds from `dist/claude-marketplace`
- [x] Isolated local-wrapper install succeeds for `simflow@simflow-claude-marketplace`
- [x] `claude plugin details simflow@simflow-claude-marketplace` lists 18 skills including `simflow-gpumd` and `simflow-mlp`
- [x] Installed plugin cache contains all seven SimFlow MCP server configs
- [ ] Claude details inventory reports MCP servers as active components
- [ ] Interactive `/simflow:simflow`, `/simflow:simflow-vasp`, `/simflow:simflow-cp2k`, `/simflow:simflow-gpumd`, `/simflow:simflow-mlp`, and `/simflow:simflow-writing` routing verified in a live Claude Code session
- [x] Real submit remains blocked without dry-run evidence, matching hashes,
      credential scan, and explicit approval

Notes:

```text
2026-06-14: Local wrapper marketplace add/install/details succeeded from
dist/claude-marketplace in an isolated /tmp HOME. Installed cache includes
.claude.mcp.json with seven mcpServers. Claude details displayed Skills (18)
but MCP servers (0), so live-session MCP activation remains an open host smoke
item.
```

## Known Limitations For Release Notes

- Supported engine helpers: VASP and CP2K are the mature workflow paths; LAMMPS has safe dry-run/input inspection plus analysis_visualization traceability.
- Limited GPUMD/NEP helper capabilities: static input inspection, manifest generation, selected output parsing, and evidence handoff only; GPUMD/NEP remain tool-level `tracked_only`.
- Generic MLP helper scope: dataset, training, validation, active-learning, production-readiness, and handoff evidence guidance across MLP tools; it is not a concrete software executor.
- Unsupported placeholders: QE and Gaussian remain placeholder skills, not supported workflow executors.
- Manual warnings: Real local, remote, or HPC execution remains blocked without dry-run evidence, hash checks, credential scan, and explicit approval.
- Follow-up issues: Complete manual Codex/Claude install smoke checks after publishing; continue post-0.8.12 install smoke verification.
