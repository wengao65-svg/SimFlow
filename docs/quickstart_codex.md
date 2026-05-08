# SimFlow v0.8.6 Codex Quick Start

This guide uses the Codex plugin installation path. SimFlow is not exposed as a primary CLI; users interact with it through Codex plugins, skills, and MCP tools.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI Codex installed

## 1. Install the published marketplace

Regular users install SimFlow from the published `codex-marketplace` branch. They do not need to clone the source repository.

```bash
codex plugin marketplace add <org>/simflow --ref codex-marketplace
codex
```

The `codex-marketplace` branch contains the Codex marketplace wrapper:

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
schemas/
templates/
workflow/
scripts/start_mcp_server.py
README.md
LICENSE
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

The source repository `main` branch is not the user install path. Current Codex CLI builds reject root-local plugin entries such as `source.path: "./"`, so SimFlow publishes an auto-generated marketplace wrapper on the `codex-marketplace` branch.

## 2. Install with `/plugins`

In Codex:

```text
/plugins
```

Expected blocking result:

- The `SimFlow` marketplace is visible.
- The `simflow` plugin is visible.
- The plugin can be installed and enabled without manifest or path errors.

## 3. Update SimFlow

```bash
codex plugin marketplace upgrade simflow-marketplace
```

After upgrading, restart Codex or open a new thread. If needed, use `/plugins` to update or reinstall `simflow`.

## 4. Developer local debugging

Developers can still test from a source checkout:

```bash
git clone <repo> ~/simflow
cd ~/simflow
npm install
npm run install:codex
codex
```

`npm run install:codex` builds a local wrapper marketplace at:

```text
~/.cache/simflow/codex-marketplace
```

Then it runs the equivalent of:

```bash
codex plugin marketplace remove simflow-local || true
codex plugin marketplace add ~/.cache/simflow/codex-marketplace
```

This local debugging path uses the same wrapper shape as the published branch.

## 5. Publish the marketplace branch

Maintainers publish from `main` to the same repository's `codex-marketplace` branch:

```bash
npm run build:codex-marketplace
npm run publish:codex-marketplace
```

`npm run build:codex-marketplace` writes:

```text
dist/codex-marketplace/.agents/plugins/marketplace.json
dist/codex-marketplace/plugins/simflow/
```

`publish:codex-marketplace` replaces the branch contents with that generated wrapper and pushes it. The branch intentionally excludes tests, `node_modules`, caches, `.simflow`, `dist`, POTCAR files, and other local or restricted-license artifacts.

## 6. Verify MCP with `/mcp`

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

## 7. Verify skills by triggering them

Blocking skill acceptance is based on valid `SKILL.md` frontmatter plus real trigger behavior after plugin install.

Use one of:

```text
$simflow
```

```text
$simflow-vasp
```

```text
@simflow-vasp
```

Or a natural-language task:

```text
Use SimFlow to plan a dry-run VASP relaxation workflow for silicon.
```

`/simflow` is not a SimFlow invocation path. Use `/plugins` to install the plugin, `/mcp` to inspect MCP servers, and skill routing such as `$simflow`, `$simflow-vasp`, or `@simflow-vasp` for SimFlow work.

`/skills` may be used as an enhanced check when the current Codex build supports it, but it is not a release-blocking acceptance criterion.

## 8. Run repository validation

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
npm run build:codex-marketplace
SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin
```

## Hook separation

`hooks/internal_workflow_hooks.json` and `hooks/*.md` are SimFlow workflow-stage hooks. They are not Codex lifecycle hooks and are not referenced from `plugin.json`.

If SimFlow later adds Codex lifecycle hooks, they must be defined in a dedicated lifecycle JSON file such as `hooks/hooks.json`, and `plugin.json` must point to that file explicitly.

## Safety defaults

- Compute and HPC operations default to dry-run behavior.
- Real HPC submission requires an explicit approval gate.
- Credentials must come from environment variables and must not be written to state, artifacts, or logs.
