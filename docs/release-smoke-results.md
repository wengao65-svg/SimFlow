# Release Smoke Results

Use this file as the local release record before publishing a version. Replace
the unchecked boxes with results from the candidate commit. Do not record
credentials, hostnames that should remain private, or proprietary file content.

## Candidate

- Version: 0.8.12
- Source candidate commit: `70f3447b5651a771d788a804e45bacb2573cb31e`
- Codex marketplace candidate commit: `272f2c7055bdd5eddc93a2e98088b7fa56b32a81`
- Claude marketplace candidate commit: `d9231c713b5ab367066f82e6751f9fa1c52353f2`
- Date: 2026-06-04
- Operator: Codex validation with planned three-branch atomic remote push

## Automated Gates

- [x] `git status --short --branch` clean except ignored local `.simflow/` and `dist/`
- [x] `python -m pytest tests/ -q`: 535 passed, 7 skipped
- [x] `npm run validate:all`: 0 errors
- [x] `python scripts/audit_skill_scripts.py`: all helper contracts OK
- [x] `npm run validate:release`: 0 errors
- [x] `npm run build:codex-marketplace`
- [x] `SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin`: 0 errors
- [x] `npm run build:claude-marketplace`
- [x] `SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin`: 0 errors

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
Not run in this workspace before the 0.8.12 remote push.
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
Not run in this workspace before the 0.8.12 remote push.
```

## Known Limitations For Release Notes

- Supported engine helpers: VASP and CP2K are the mature workflow paths; LAMMPS has safe dry-run/input inspection plus analysis_visualization traceability.
- Unsupported placeholders: QE and Gaussian remain placeholder skills, not supported workflow executors.
- Manual warnings: Real local, remote, or HPC execution remains blocked without dry-run evidence, hash checks, credential scan, and explicit approval.
- Follow-up issues: Complete manual Codex/Claude install smoke checks after publishing; continue post-0.8.12 install smoke verification.
