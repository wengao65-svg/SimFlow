# SimFlow v0.8.5 Codex Quick Start

This guide uses the Codex plugin installation path. SimFlow is not exposed as a primary CLI; users interact with it through Codex plugins, skills, and MCP tools.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI Codex installed

## 1. Install from the SimFlow repository

Clone SimFlow, install development dependencies, and register the local Codex marketplace wrapper:

```bash
git clone <repo> ~/simflow
cd ~/simflow
npm install
npm run install:codex
```

`npm run install:codex` builds a wrapper marketplace at:

```text
~/.cache/simflow/codex-marketplace
```

Then it runs the equivalent of:

```bash
codex plugin marketplace remove simflow-local || true
codex plugin marketplace add ~/.cache/simflow/codex-marketplace
```

The wrapper contains:

```text
.agents/plugins/marketplace.json
plugins/simflow/
```

Inside `plugins/simflow/`, the copied plugin root includes:

```text
.codex-plugin/plugin.json
.mcp.json
skills/
mcp/
runtime/
scripts/start_mcp_server.py
```

The wrapper marketplace entry points at the copied plugin directory:

```json
{
  "name": "simflow",
  "source": {
    "source": "local",
    "path": "./plugins/simflow"
  }
}
```

The source repository root is not the default marketplace root. Current Codex CLI builds reject root-local plugin entries such as `source.path: "./"`, so the repository `.agents/plugins/marketplace.json` is intentionally not the user install path.

## 2. Install with `/plugins`

Start Codex:

```bash
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

Remote installation is supported when the remote repository is a wrapper marketplace with `.agents/plugins/marketplace.json` and a real `plugins/simflow/` directory:

```bash
codex plugin marketplace add <org>/simflow --ref <version>
```

The remote marketplace entry must use `source.path: "./plugins/simflow"`.

## 4. Optional clean marketplace wrapper

Maintainers can still generate a clean wrapper for publishing to a separate marketplace repository or as a release artifact:

```bash
npm run build:marketplace
```

The default wrapper is:

```text
~/.cache/simflow/codex-marketplace
```

It contains:

```text
.agents/plugins/marketplace.json
plugins/simflow/
```

`plugins/simflow` is a real copied plugin directory, not a symlink. This same wrapper structure is used by the default `npm run install:codex` flow.

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

If `/mcp` does not list them, run `npm run validate:plugin` from the source repository to check the manifest, marketplace path rules, and JSON-RPC stdio initialization.

## 6. Verify skills by triggering them

Blocking skill acceptance is based on valid `SKILL.md` frontmatter plus real trigger behavior after plugin install.

Use one of:

```text
$simflow
```

```text
$simflow-vasp
```

```text
@simflow
```

Or a natural-language task:

```text
Use SimFlow to plan a dry-run VASP relaxation workflow for silicon.
```

`/simflow` is not a SimFlow invocation path. Use `/plugins` to install the plugin, `/mcp` to inspect MCP servers, and skill routing such as `$simflow`, `$simflow-vasp`, or `@simflow` for SimFlow work.

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
- marketplace local source paths reject empty, `.`, and `./`
- wrapper marketplace structure when `SIMFLOW_MARKETPLACE_ROOT` is set
- separation between SimFlow workflow hooks and Codex lifecycle hooks

To validate an optional wrapper after building it:

```bash
npm run build:marketplace
SIMFLOW_MARKETPLACE_ROOT=~/.cache/simflow/codex-marketplace npm run validate:plugin
```

## Hook separation

`hooks/internal_workflow_hooks.json` and `hooks/*.md` are SimFlow workflow-stage hooks. They are not Codex lifecycle hooks and are not referenced from `plugin.json`.

If SimFlow later adds Codex lifecycle hooks, they must be defined in a dedicated lifecycle JSON file such as `hooks/hooks.json`, and `plugin.json` must point to that file explicitly.

## Safety defaults

- Compute and HPC operations default to dry-run behavior.
- Real HPC submission requires an explicit approval gate.
- Credentials must come from environment variables and must not be written to state, artifacts, or logs.
