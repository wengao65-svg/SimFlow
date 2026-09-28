# SimFlow

SimFlow is a portable Skill Pack for AI-assisted computational simulation. It
helps an agent review scientific literature, prepare and inspect models and
inputs, interpret outputs, analyze data, and draft research writing. The user
owns the scientific question, experimental decisions, and research records.

The public pack contains seven Research Task Skills and five Domain Skills for
VASP, CP2K, LAMMPS, GPUMD/NEP, and machine-learning interatomic potentials.
Each Skill has a `SKILL.md` and, where useful, focused references and standalone
scripts. Skills can be
combined with the host agent's ordinary tools and other Skills.

SimFlow no longer installs an MCP server or an experiment-management runtime.
Using a Skill does not create `.simflow/`, register artifacts, or require a
checkpoint. Existing project data stays in the user's chosen layout. Real
computation, remote writes, and scheduler submission follow the user's
concrete authorization and the host's permissions. Scientific validity must
still be judged from inputs, diagnostics, and outputs; a successful submission
or parser result alone is insufficient.

## Install

For Codex, add the published marketplace and install `simflow` through
`/plugins`:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
```

For Claude Code:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For OpenCode:

```bash
opencode plugin opencode-simflow --global
```

See [installation](docs/installation.md) for local development and verification.
The [Skill Pack direction](docs/direction-skill-pack.md) explains the evidence
and migration plan behind this refactor.

## Development

```bash
npm run validate:all
npm run build:codex-marketplace
npm run build:claude-marketplace
npm run build:opencode-plugin
python -m pytest tests/ -q
```

The source and all three installation packages include self-contained scientific
helpers inside their Skills. The legacy runtime, MCP, workflow, and schema
layers have been retired. See [skills/README.md](skills/README.md) for usage.

Licensed VASP POTCAR content, credentials, and private keys must never be
committed or distributed. The repository is licensed under [MIT](LICENSE).
