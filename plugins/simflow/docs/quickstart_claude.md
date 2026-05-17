# SimFlow Claude Code Quick Start

This guide uses the Claude Code plugin marketplace path. SimFlow remains skill-driven: users interact through Claude plugin skills and MCP tools, not through a primary SimFlow CLI.

## Prerequisites

- Python 3.10+
- Node.js 18+ for repository validation
- Claude Code installed

## Install the Published Marketplace

Regular users install the published Claude marketplace branch. Claude Code pins marketplace refs in the source string:

```bash
claude plugin marketplace add <org>/simflow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For a generic git URL, use `#ref`:

```bash
claude plugin marketplace add https://github.com/<org>/simflow.git#claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

`claude plugin marketplace add` supports `--scope` and `--sparse`. It does not use a `--ref` option.

## Developer Local Test

Build and install the local Claude marketplace wrapper:

```bash
git clone <repo> ~/simflow
cd ~/simflow
npm install
npm run build:claude-marketplace
claude plugin marketplace add ./dist/claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

The wrapper contains:

```text
.claude-plugin/marketplace.json
plugins/simflow/
```

Inside `plugins/simflow/`, the copied plugin root includes:

```text
.claude-plugin/plugin.json
.claude.mcp.json
skills/
agents/
mcp/
runtime/
schemas/
templates/
workflow/
scripts/start_mcp_server.py
README.md
LICENSE
```

The marketplace entry uses the Claude relative-path source form:

```json
{
  "name": "simflow",
  "source": "./plugins/simflow"
}
```

## Verify

Validate the source checkout:

```bash
npm run validate:claude-plugin
```

Validate the built wrapper:

```bash
npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

When the Claude CLI is available, also run:

```bash
claude plugin validate dist/claude-marketplace
claude plugin details simflow@simflow-claude-marketplace
```

## Use SimFlow Skills

Claude plugin skills are namespaced by plugin name. Typical invocations are:

```text
/simflow:simflow
/simflow:simflow-vasp
/simflow:simflow-cp2k
/simflow:simflow-writing
```

Natural-language routing also works when Claude Code selects the installed SimFlow skills.

## MCP Servers

The Claude adapter uses `.claude.mcp.json`, which points to the existing SimFlow MCP startup wrapper through `${CLAUDE_PLUGIN_ROOT}`. It should expose:

- `simflow_state`
- `artifact_store`
- `checkpoint_store`
- `literature`
- `structure`
- `hpc`
- `parsers`

Real HPC submission remains blocked unless the existing SimFlow approval gate is explicitly passed.

