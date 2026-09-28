# SimFlow for OpenCode

Install the published Skill-only package:

```bash
opencode plugin opencode-simflow --global
```

The adapter adds the 12 SimFlow Skills to OpenCode discovery. It does not add
or modify MCP servers. Check discovery with `opencode debug skill`, then ask a
scientific question or load a relevant Skill.

For local development:

```bash
npm run build:opencode-plugin
SIMFLOW_OPENCODE_PLUGIN_ROOT=dist/opencode-plugin npm run validate:opencode-plugin
```

Real compute or scheduler submission follows OpenCode's permissions and the
user's authorization for the concrete action. Inspect outputs before judging
scientific completion.
