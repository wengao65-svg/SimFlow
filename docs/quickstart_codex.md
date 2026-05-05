# SimFlow v0.8.0 Codex Quick Start

This guide uses the Codex plugin installation path. SimFlow is not exposed as a primary CLI; users interact with it through Codex plugins, skills, and MCP tools.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI Codex installed

## 1. Build the local marketplace wrapper

From the SimFlow repository root:

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

`plugins/simflow` is a real copied plugin directory, not a symlink. The marketplace entry uses the official local source shape:

```json
{
  "name": "simflow",
  "source": {
    "source": "local",
    "path": "./plugins/simflow"
  }
}
```

## 2. Install with `/plugins`

Start Codex from the wrapper root:

```bash
cd /home/gaofeng/test/SimFlow-marketplace
codex
```

In Codex:

```text
/plugins
```

Expected blocking result:

- The `SimFlow Local Plugins` marketplace is visible.
- The `simflow` plugin is visible.
- The plugin can be installed and enabled without manifest or path errors.

## 3. Verify MCP with `/mcp`

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

If `/mcp` does not list them, run `npm run validate:plugin` from the source repository to check the manifest, wrapper, and JSON-RPC stdio initialization.

## 4. Verify skills by triggering them

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

## 5. Run repository validation

From the SimFlow source repository:

```bash
npm run build:marketplace
npm run validate:plugin
npm run validate:skills
npm run validate:schemas
```

`validate:plugin` checks:

- `.codex-plugin/plugin.json` metadata and interface fields
- root `.mcp.json`
- JSON-RPC stdio MCP initialization and `tools/list`
- external marketplace wrapper structure
- separation between SimFlow workflow hooks and Codex lifecycle hooks

## Hook separation

`hooks/internal_workflow_hooks.json` and `hooks/*.md` are SimFlow workflow-stage hooks. They are not Codex lifecycle hooks and are not referenced from `plugin.json`.

If SimFlow later adds Codex lifecycle hooks, they must be defined in a dedicated lifecycle JSON file such as `hooks/hooks.json`, and `plugin.json` must point to that file explicitly.

## Safety defaults

- Compute and HPC operations default to dry-run behavior.
- Real HPC submission requires an explicit approval gate.
- Credentials must come from environment variables and must not be written to state, artifacts, or logs.
