# SimFlow for Codex

Install the published Skill-only marketplace:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
codex
```

Open `/plugins` and install `simflow`. The plugin provides 12 Research Task and
Domain Skills, including `$simflow-vasp`, `$simflow-cp2k`, and
`$simflow-analysis-visualization`. Ask a natural-language research question or
invoke a relevant Skill directly. Installation adds no SimFlow MCP server and
creates no `.simflow/` project state.

For local development:

```bash
npm run build:codex-marketplace
SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin
```

Real compute or scheduler submission uses the host's ordinary tools, its
permission system, and the user's authorization for the concrete action. Read
scientific outputs before claiming convergence or completion.
