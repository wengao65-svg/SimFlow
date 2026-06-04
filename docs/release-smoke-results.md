# Release Smoke Results

Use this file as the local release record before publishing a version. Replace
the unchecked boxes with results from the candidate commit. Do not record
credentials, hostnames that should remain private, or proprietary file content.

## Candidate

- Version: 0.8.11
- Source commit: `713e4e8d335c1136a15fce2f94303a7f3f92497c`
- Codex marketplace commit: `22e41fcde70df8569fd418c96cbf23825b7f4bbf`
- Claude marketplace commit: `837626beac14ca3819cc60f795890ea18346fed8`
- Date: 2026-05-31
- Operator: Codex validation plus user manual remote push

## Automated Gates

- [x] `git status --short` clean except ignored local runtime/build artifacts
- [x] `python -m pytest tests/ -q`
- [x] `npm run validate:all`
- [x] `python scripts/audit_skill_scripts.py`
- [x] `npm run validate:release -- --skip-wrapper-build`
- [x] `npm run build:codex-marketplace`
- [x] `SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin`
- [x] `npm run build:claude-marketplace`
- [x] `SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin`

## Codex Install Smoke

- [ ] `codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace`
- [ ] `/plugins` shows and installs `simflow`
- [ ] `/mcp` shows all seven SimFlow MCP servers
- [ ] `$simflow` routes to the core skill
- [ ] `$simflow-vasp` routes to the VASP helper
- [ ] Real submit remains blocked without dry-run evidence, matching hashes,
      credential scan, and explicit approval

Notes:

```text
Not run in this workspace after the manual remote push.
```

## Claude Code Install Smoke

- [ ] `claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace`
- [ ] `claude plugin install simflow@simflow-claude-marketplace`
- [ ] `claude plugin details simflow@simflow-claude-marketplace`
- [ ] `/simflow:simflow` routes to the core skill
- [ ] `/simflow:simflow-vasp` routes to the VASP helper
- [ ] `/simflow:simflow-cp2k` routes to the CP2K helper
- [ ] `/simflow:simflow-writing` routes to the writing skill
- [ ] Real submit remains blocked without dry-run evidence, matching hashes,
      credential scan, and explicit approval

Notes:

```text
Not run in this workspace after the manual remote push.
```

## Known Limitations For Release Notes

- Supported engine helpers: VASP and CP2K are the mature workflow paths; LAMMPS has safe dry-run/input inspection plus improving analysis support.
- Unsupported placeholders: QE and Gaussian remain placeholder skills, not supported workflow executors.
- Manual warnings: Real local, remote, or HPC execution remains blocked without dry-run evidence, hash checks, credential scan, and explicit approval.
- Follow-up issues: Complete manual Codex/Claude install smoke checks; continue 0.8.12 work on LAMMPS analysis_visualization traceability.
