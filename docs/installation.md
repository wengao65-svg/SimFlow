# Installation

SimFlow is distributed as a Skill-only plugin for Codex, Claude Code, and
OpenCode. The packages include 12 Skills and focused references. They do not
install SimFlow MCP servers, a workflow runtime, or experiment state.

## Codex

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
```

Install `simflow` with `/plugins`. Verify a Skill such as `$simflow-vasp`.

## Claude Code

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Try `/simflow:simflow-cp2k` or another relevant Skill.

## OpenCode

```bash
opencode plugin opencode-simflow --global
opencode debug skill
```

The OpenCode adapter adds a Skills path and preserves existing user MCP
configuration.

## Source development

Node.js 18+ and Python 3.10+ are recommended for repository checks. Build and
validate all three packages from the source checkout:

```bash
npm run validate:all
npm run build:codex-marketplace
SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
npm run build:opencode-plugin
SIMFLOW_OPENCODE_PLUGIN_ROOT=dist/opencode-plugin npm run validate:opencode-plugin
```

Each package includes standalone Skill scripts, local `lib/` code, and assets.
The old runtime, MCP, workflow, and schema layers are retired. Install the
relevant optional Python dependencies before running a scientific helper.
Existing `.simflow/` directories are user data and are not changed by
installation.

Skills guide preparation and review. Actual execution uses host tools and
permissions, with user authorization for the concrete action where required.
POTCAR content and credentials must stay out of published packages and logs.

Optional scientific scripts have per-Skill `requirements.txt` files. See
[helper dependencies](helper-dependencies.md) for installation and scope.
