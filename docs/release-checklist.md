# SimFlow Release Acceptance Checklist

Use this checklist before announcing, tagging, or publishing a SimFlow release.
It covers the source checkout and the generated Codex and Claude marketplace
wrappers.

## 1. Source Tree Gate

Start from the source repository root:

```bash
git status --short
git log --oneline -n 5
python -m pytest tests/ -q
npm run validate:all
python scripts/audit_skill_scripts.py
npm run validate:release -- --skip-wrapper-build
```

Expected result:

- `git status --short` is clean except for intentionally ignored local runtime
  state.
- The full Python test suite passes.
- Codex plugin, Claude plugin, skills, and schemas validate with zero errors.
- Skill script contract audit reports `OK` for all packaged helper scripts.

## 2. Restricted Artifact Gate

Real licensed or large VASP runtime artifacts must not be tracked or packaged.

Run:

```bash
git ls-files | grep -E '__pycache__|\.pyc$|^dist/|\.pytest_cache|POTCAR$|WAVECAR|CHGCAR|OUTCAR|vasprun\.xml' || true
find examples/si_band_structure -name POTCAR -o -name WAVECAR -o -name CHGCAR -o -name OUTCAR -o -name vasprun.xml
git ls-files examples/si_band_structure | grep -E 'POTCAR|WAVECAR|CHGCAR|OUTCAR|vasprun\.xml' || true
```

Expected result:

- No tracked generated caches or `dist/` files.
- No real VASP runtime artifacts are present in `examples/si_band_structure`.
- The only allowed tracked POTCAR-related files are
  `POTCAR.metadata.json` placeholders.

Stop the release if any real `POTCAR`, `WAVECAR`, `CHGCAR`, `OUTCAR`, or
`vasprun.xml` appears outside explicitly synthetic test fixtures.

## 3. Safe Example Gate

Run the redistributable dry-run example into a disposable directory:

```bash
tmpdir="$(mktemp -d)"
python examples/safe_dry_run/run_example.py --project-root "$tmpdir"
python examples/si_band_structure/validate_inputs.py
python examples/h2o/run_cp2k_workflow.py --dry-run
```

Expected result:

- The safe example produces `.simflow/` state, artifact registry,
  checkpoints, dry-run computation evidence, credential scan evidence, and
  handoff reports under the disposable project root.
- The Si example validates committed input metadata without requiring real
  POTCAR content.
- The H2O CP2K example can run in dry-run mode without HPC credentials.

## 4. Public Metadata Gate

Run:

```bash
rg -n "maintainers@example|github.com/simflow|simflow/simflow" .codex-plugin .claude-plugin scripts dist -S || true
```

Expected result:

- No placeholder maintainer email.
- No placeholder `github.com/simflow` repository metadata.
- Public metadata points to `https://github.com/wengao65-svg/SimFlow`.

## 5. Marketplace Wrapper Gate

For the full automated release gate from a clean tree, run:

```bash
npm run validate:release
```

Build and validate the Codex wrapper:

```bash
npm run build:codex-marketplace
SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin
```

Build and validate the Claude wrapper:

```bash
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

Expected result:

- Both wrappers are real directories, not symlinks.
- Both wrappers include skills, MCP servers, runtime, workflow, schemas,
  templates, docs, `scripts/start_mcp_server.py`, README, and LICENSE.
- Both wrappers exclude tests, caches, `.simflow/`, `.omx/`, `dist/`, legacy
  removed source paths, and restricted VASP artifacts.
- MCP stdio initialization and `tools/list` pass for all configured servers.

## 6. Release Notes Gate

Generate local release notes before tagging or publishing:

```bash
npm run release:notes -- --since=<previous-release-ref>
```

Expected result:

- The output includes the target version, target commit, release gates, and
  commit summary.
- Any manual install-smoke results or known limitations are added to the final
  release notes before publishing.

## 7. Manual Install Smoke Gate

Codex user path:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
codex
```

Inside Codex:

```text
/plugins
/mcp
$simflow
$simflow-vasp
```

Claude Code user path:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
claude plugin details simflow@simflow-claude-marketplace
```

Inside Claude Code:

```text
/simflow:simflow
/simflow:simflow-vasp
/simflow:simflow-cp2k
/simflow:simflow-writing
```

Expected result:

- Plugin install succeeds.
- All seven MCP servers initialize:
  `simflow_state`, `artifact_store`, `checkpoint_store`, `literature`,
  `structure`, `hpc`, and `parsers`.
- Skill routing works through the host agent.
- Real local, remote, or HPC submission remains blocked without dry-run
  evidence, matching hashes, credential scan, and explicit approval.

## 8. Release Ref Rules

- Do not push `.simflow/`, `dist/`, caches, or generated local artifacts.
- Do not force-push release refs without explicit maintainer confirmation.
- Do not move `workflow-layer-refactor-v1` unless the task explicitly requires
  rewriting that stable ref.
- Do not publish marketplace branches from an unvalidated source checkout.
- If restricted scientific artifacts are found in Git history, stop ordinary
  release work and run a controlled history cleanup before pushing.
