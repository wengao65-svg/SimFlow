# Claude Marketplace Release

Build and validate the Skill-only wrapper:

```bash
npm run validate:claude-plugin
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

A publish dry run is available with
`npm run publish:claude-marketplace -- --dry-run`. Review the generated branch
content: `plugins/simflow/` should contain the plugin manifest, 12 Skill
folders with their scripts and local resources, references, and public docs. It must exclude `.claude.mcp.json`,
`mcp/`, `runtime/`, `workflow/`, and `schemas/`.

Publish with `npm run publish:claude-marketplace`, then install the branch in a
fresh Claude Code environment and verify a relevant Skill such as
`/simflow:simflow-vasp` can be discovered. Installation must not register a
SimFlow MCP server or create `.simflow/` state.
