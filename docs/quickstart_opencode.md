# SimFlow OpenCode Quick Start

SimFlow supports stable OpenCode `1.18.9 <= version < 2` through the
`opencode-simflow` npm plugin. The V2 beta plugin API is not part of this
compatibility contract.

## Requirements

- OpenCode 1.18.9 or a later stable 1.x release
- Python 3.10+
- Linux, macOS, or WSL2

The adapter does not configure providers, models, credentials, permissions, or
automatic execution.

## Install

Install SimFlow for all OpenCode projects:

```bash
opencode plugin opencode-simflow --global
```

For one project only, run the command without `--global` from that project:

```bash
opencode plugin opencode-simflow
```

Update or replace the installed version:

```bash
opencode plugin opencode-simflow --global --force
```

## Verify

Inspect the resolved configuration, skills, and MCP servers:

```bash
opencode debug config
opencode debug skill
opencode mcp list
```

The plugin exposes the canonical SimFlow skills and these MCP server names:

```text
simflow_state
artifact_store
checkpoint_store
literature
structure
hpc
parsers
```

Ask OpenCode to use `simflow`, `simflow-vasp`, `simflow-cp2k`, or another
bundled skill. Skills remain guidance and evidence contracts; they do not turn
SimFlow into a workflow executor.

## Python Interpreter

The adapter starts MCP servers with `python3` by default. Override the
interpreter when SimFlow is installed in a virtual environment:

```bash
export SIMFLOW_PYTHON=/path/to/venv/bin/python
opencode
```

The value is passed as a command-array element, not through a shell.

## Existing MCP Names

User configuration wins when an OpenCode configuration already defines one of
the seven SimFlow MCP names. The plugin preserves the existing entry and writes
a warning containing only the conflicting server name. Resolve the collision
in `opencode.json` before relying on that SimFlow server.

## Source Checkout

When OpenCode starts from the SimFlow source repository, it automatically loads
`.opencode/plugins/simflow.js`. No global installation is required for local
development.

Build and validate the publishable package:

```bash
npm run build:opencode-plugin
SIMFLOW_OPENCODE_PLUGIN_ROOT=dist/opencode-plugin npm run validate:opencode-plugin
node scripts/smoke_opencode_plugin.js dist/opencode-plugin
```

The isolated smoke test uses temporary HOME and XDG directories. It does not
read the developer's provider configuration or invoke a model.

## Publishing

Maintainers can inspect the package without publishing:

```bash
npm run publish:opencode-plugin -- --dry-run
```

Real npm publication requires the manual OpenCode release workflow, an
authorized repository Actions secret named `SIMFLOW`, completed release gates,
and explicit approval. It is
not triggered by ordinary pushes to `main`.
