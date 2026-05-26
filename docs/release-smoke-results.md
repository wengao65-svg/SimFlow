# Release Smoke Results

Use this file as the local release record before publishing a version. Replace
the unchecked boxes with results from the candidate commit. Do not record
credentials, hostnames that should remain private, or proprietary file content.

## Candidate

- Version:
- Source commit:
- Codex marketplace commit:
- Claude marketplace commit:
- Date:
- Operator:

## Automated Gates

- [ ] `git status --short` clean except ignored local runtime/build artifacts
- [ ] `python -m pytest tests/ -q`
- [ ] `npm run validate:all`
- [ ] `python scripts/audit_skill_scripts.py`
- [ ] `npm run validate:release`
- [ ] `npm run build:codex-marketplace`
- [ ] `SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin`
- [ ] `npm run build:claude-marketplace`
- [ ] `SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin`

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
```

## Known Limitations For Release Notes

- Supported engine helpers:
- Unsupported placeholders:
- Manual warnings:
- Follow-up issues:
