# Skill Pack Release Checklist

Before publishing, run `SIMFLOW_RELEASE_ALLOW_DIRTY=1 npm run validate:release`
for a review checkout, then run `npm run validate:release` from a clean release
commit. The validator builds Codex, Claude Code, and OpenCode packages and checks
that each contains exactly 12 Skills, runnable self-contained scripts, no SimFlow
MCP or workflow state, and no restricted VASP artifacts.

Review the version change across `package.json`, `pyproject.toml`, both plugin
manifests, and `.codex/config.toml`. Marketplace skill changes require a new
plugin version. Do not publish a package that still points to removed helpers
or requires `hpc/submit`, `run_plan_hash`, or SimFlow approval records.

Smoke-test Skill discovery in each host when the CLI is available. Check that
ordinary Skill use does not create `.simflow/` and that OpenCode preserves any
MCP configuration the user already supplied. Real execution remains governed
by the host's permission system and the user's authorization.

Publication changes marketplace branches or the npm registry and requires the
maintainer's release authorization.
