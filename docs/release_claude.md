# SimFlow Claude Marketplace Release

Use this checklist to publish the Claude Code adapter. This is independent of the Codex marketplace release path.

## Build and Validate

```bash
npm run validate:claude-plugin
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

When Claude Code is available locally:

```bash
claude plugin validate dist/claude-marketplace
```

## Dry Run Publish

```bash
npm run publish:claude-marketplace -- --dry-run
```

Inspect the generated worktree path printed by the command. Confirm it contains:

```text
.claude-plugin/marketplace.json
plugins/simflow/.claude-plugin/plugin.json
plugins/simflow/.claude.mcp.json
plugins/simflow/skills/
plugins/simflow/mcp/
plugins/simflow/runtime/
```

## Publish

```bash
npm run publish:claude-marketplace
```

This replaces the `claude-marketplace` branch contents with `dist/claude-marketplace`.

## User Smoke Test

```bash
claude plugin marketplace add <org>/simflow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
claude plugin details simflow@simflow-claude-marketplace
```

For git URLs, use `#claude-marketplace`:

```bash
claude plugin marketplace add https://github.com/<org>/simflow.git#claude-marketplace
```

Verify these skill invocations:

```text
/simflow:simflow
/simflow:simflow-vasp
/simflow:simflow-cp2k
/simflow:simflow-writing
```

Verify the installed plugin exposes the seven SimFlow MCP servers and that real HPC submission still requires explicit approval.

