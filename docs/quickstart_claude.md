# SimFlow for Claude Code

Install the published Skill-only marketplace:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Use a natural-language task or a relevant namespaced Skill such as
`/simflow:simflow-vasp`, `/simflow:simflow-cp2k`, or
`/simflow:simflow-writing`. The plugin installs 12 Skills and no SimFlow MCP
server. It does not create a SimFlow experiment notebook.

For local development:

```bash
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

Real compute or scheduler submission uses the host's permissions and the
user's authorization for the concrete action. A submitted job is not proof
of a converged scientific result.
