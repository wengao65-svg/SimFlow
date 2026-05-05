# SimFlow v0.8.2 Codex Quick Start

This guide uses the Codex plugin installation path. SimFlow is not exposed as a primary CLI; users interact with it through Codex plugins, skills, and MCP tools.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI Codex installed

## 1. Install from the SimFlow repository

The SimFlow repository root is both the Codex marketplace root and the plugin root. Clone it, install development dependencies, and validate the plugin structure:

```bash
git clone <repo> ~/simflow
cd ~/simflow
npm install
npm run validate
```

The repository includes:

```text
.agents/plugins/marketplace.json
.codex-plugin/plugin.json
.mcp.json
skills/
mcp/
runtime/
scripts/start_mcp_server.py
```

The default marketplace entry points back to this repository root:

```json
{
  "name": "simflow",
  "source": {
    "source": "local",
    "path": "./"
  }
}
```

## 2. Install with `/plugins`

Register the local marketplace and start Codex:

```bash
codex plugin marketplace add ~/simflow
codex
```

In Codex:

```text
/plugins
```

Expected blocking result:

- The `SimFlow` marketplace is visible.
- The `simflow` plugin is visible.
- The plugin can be installed and enabled without manifest or path errors.

## 3. Remote marketplace installation

Remote installation is supported when the remote repository contains `.agents/plugins/marketplace.json`:

```bash
codex plugin marketplace add <org>/simflow --ref <version>
```

This uses the same repository-root plugin layout as the local install path.

## 4. Optional clean marketplace wrapper

Maintainers can still generate a clean wrapper for publishing to a separate marketplace repository or as a release artifact:

```bash
npm run build:marketplace
```

The default wrapper is:

```text
/home/gaofeng/test/SimFlow-marketplace
```

It contains:

```text
.agents/plugins/marketplace.json
plugins/simflow/
```

`plugins/simflow` is a real copied plugin directory, not a symlink. This wrapper is optional and is not required for normal user installation.

## 5. Verify MCP with `/mcp`

After installing the plugin, run:

```text
/mcp
```

Expected blocking result: Codex initializes and lists these SimFlow MCP servers:

- `simflow_state`
- `artifact_store`
- `checkpoint_store`
- `literature`
- `structure`
- `hpc`
- `parsers`

If `/mcp` does not list them, run `npm run validate:plugin` from the source repository to check the manifest, root marketplace, and JSON-RPC stdio initialization.

## 6. Verify skills by triggering them

Blocking skill acceptance is based on valid `SKILL.md` frontmatter plus real trigger behavior after plugin install.

Use one of:

```text
$simflow
```

```text
$simflow-vasp
```

Or a natural-language task:

```text
Use SimFlow to plan a dry-run VASP relaxation workflow for silicon.
```

`/skills` may be used as an enhanced check when the current Codex build supports it, but it is not a release-blocking acceptance criterion.

## 7. Run repository validation

From the SimFlow source repository:

```bash
npm run validate
```

`validate:plugin` checks:

- `.codex-plugin/plugin.json` metadata and interface fields
- root `.mcp.json`
- JSON-RPC stdio MCP initialization and `tools/list`
- repository-root `.agents/plugins/marketplace.json`
- repository-root plugin structure
- separation between SimFlow workflow hooks and Codex lifecycle hooks

To validate an optional wrapper after building it:

```bash
npm run build:marketplace
SIMFLOW_MARKETPLACE_ROOT=/home/gaofeng/test/SimFlow-marketplace npm run validate:plugin
```

## Hook separation

`hooks/internal_workflow_hooks.json` and `hooks/*.md` are SimFlow workflow-stage hooks. They are not Codex lifecycle hooks and are not referenced from `plugin.json`.

If SimFlow later adds Codex lifecycle hooks, they must be defined in a dedicated lifecycle JSON file such as `hooks/hooks.json`, and `plugin.json` must point to that file explicitly.

## Safety defaults

- Compute and HPC operations default to dry-run behavior.
- Real HPC submission requires an explicit approval gate.
- Credentials must come from environment variables and must not be written to state, artifacts, or logs.
