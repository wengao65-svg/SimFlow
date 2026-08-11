# SimFlow

SimFlow is a computational-research guidance, provenance, recovery, and safety
layer for Codex, Claude Code, OpenCode, and compatible host agents.

It does not choose the science or execute a fixed workflow. The host agent
performs literature work, modeling, coding, computation, analysis, and writing.
SimFlow adds reusable scientific guidance and a small runtime for facts that
must be recorded or safeguarded.

## Architecture

```text
Host Agent
  -> Router                 selects at most one Task Skill + one Domain Skill
  -> Research Task Skill    how to do the current research task well
  -> Domain Skill           engine- or method-specific knowledge
  -> SimFlow Runtime        inspect, record, recover, and gate real execution
  -> .simflow/              scientific notebooks, operational truth, recovery
```

Skill selection follows current intent. Directory organization follows the
project. Runtime follows events that actually happened. These three concerns
are deliberately independent.

## Public Skills

SimFlow exposes exactly 12 Skills.

| Class | Skills |
| --- | --- |
| Router | `simflow` |
| Research Task | `simflow-literature-review`, `simflow-proposal`, `simflow-modeling`, `simflow-computation`, `simflow-analysis-visualization`, `simflow-writing` |
| Domain | `simflow-vasp`, `simflow-cp2k`, `simflow-lammps`, `simflow-gpumd`, `simflow-mlp` |

Task and Domain Skills are pure instruction bundles. They remain useful without
MCP and do not own workflow state, artifact registration, checkpoints,
approval, or directory layout.

Unsupported engines do not receive placeholder Skills. The router preserves
the requested software as context and uses the relevant Task Skill without
claiming built-in engine support.

## Public Runtime

Two MCP servers expose eight composite tools:

| Server | Tools |
| --- | --- |
| `simflow_state` | `inspect`, `record`, `checkpoint`, `recover` |
| `hpc` | `plan`, `transfer`, `submit`, `status` |

There is no engagement lifecycle, SQLite/session/activity ledger, activity
controller, or mandatory session handoff. Compact Experiment notebooks retain
scientific questions and decisions without creating a host-session lifecycle.
Ordinary read-only scientific work produces no state writes. One logical task
normally needs at most one `record` call after the automatic `hpc/plan` record.

New project state is compact:

```text
.simflow/
├── experiments/
│   ├── <experiment_id>.md
│   └── index.md
├── project.json
├── records.jsonl
├── checkpoints/
└── reports/
```

Experiment notebooks are append-only scientific memory. `records.jsonl` is the
append-only operational truth for plans, approvals, transfers, submissions,
status, logical deliverables, checkpoints, and migration confirmations. Exact
scientific files remain authoritative evidence. `project.json` and the
Experiment index are deterministic derived summaries.

Historical `.simflow/state/*.json`, `.simflow/memory/`, and nested `.simflow`
roots remain readable. `inspect` produces a metadata-only migration inventory;
SQLite tables and memory contents are never imported. Applying it requires an
exact current hash and explicit confirmation, and migration never moves or
rewrites source data.

## Safety Model

Real local, remote, and scheduler execution is dry-run and plan first.
`hpc/plan` persists an immutable identity covering:

- job script and input hashes;
- scheduler, SSH target, and remote working directory;
- resource request;
- upload/download and destructive scope;
- restricted-file metadata, including POTCAR dataset metadata.

Approval is bound to `run_plan_hash`. Unchanged retries and resumes can reuse
approval. Any material change makes the plan stale and requires a new approval.
Transfer and submit automatically append one compact run record.

SSH authentication remains host-managed behind the credential broker. MCP
payloads reject passwords, private-key content, key paths, and arbitrary SSH
options. Licensed POTCAR content may exist only in a controlled calculation
directory and is never copied into `.simflow`, Git, packages, logs, or MCP
responses.

## Project Layout

SimFlow respects existing project organization. For a new project, the six
research phases are a useful template, not a required state machine:

```text
phase1_literature_review/
phase2_proposal/
phase3_modeling/
phase4_computation/
phase5_analysis_visualization/
phase6_writing/
```

Analysis stays near the scientific inputs it consumes. Comparisons across runs
use one meaningful common analysis entry, and only project-level synthesis is
placed physically in phase 5. Shallow README indexes use relative links; they
do not copy or symlink results into a second authoritative location.

See [User Project Layout Guidance](docs/user-project-layout.md).

## Quick Start

### Claude Code

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Update with:

```bash
claude plugin marketplace update simflow-claude-marketplace
claude plugin update simflow
```

Skills are namespaced, for example `/simflow:simflow` and
`/simflow:simflow-vasp`. See [Claude Code Quick Start](docs/quickstart_claude.md).

### Codex

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
codex
```

Install `simflow` through `/plugins`, then verify with `/mcp` and `$simflow`.
Update with `codex plugin marketplace upgrade simflow-marketplace`. See
[Codex 快速上手](docs/quickstart_codex.md).

### OpenCode

```bash
opencode plugin opencode-simflow --global
```

Update with `opencode plugin opencode-simflow --global --force`. See
[OpenCode Quick Start](docs/quickstart_opencode.md).

## Repository Structure

```text
simflow/
├── skills/                    # 12 public Router, Task, and Domain Skills
├── workflow/                  # Advisory stages/recipes and runtime policies/gates
├── mcp/servers/
│   ├── simflow_state/         # Four compact state/recovery tools
│   └── hpc/                   # Four immutable-plan execution tools
├── runtime/
│   ├── simflow_core/          # Compact records, gates, recovery, compatibility
│   └── simflow_helpers/       # Optional scientific helpers and internal adapters
├── schemas/                   # Current contracts plus labeled legacy read schemas
├── tests/
├── docs/
└── scripts/
```

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MP_API_KEY` | Materials Project API key |
| `S2_API_KEY` | Semantic Scholar API key |
| `SIMFLOW_PYTHON` | Python executable used by the OpenCode MCP adapter |
| `SIMFLOW_HPC_BROKER_SOCKET` | Unix socket for isolated SSH operations |
| `SIMFLOW_HPC_BROKER_ALLOWED_ROOTS` | Project roots accessible to the broker |

Without `S2_API_KEY`, literature search uses OpenAlex. Mock literature results
are degraded, marked `mock_unverified`, and cannot be treated as evidence.

## Documentation

- [User Guide](docs/user_guide.md)
- [Skill Design](docs/skill-design.md)
- [MCP Tool Reference](docs/mcp-tool-reference.md)
- [State And Recovery](docs/state-and-checkpoint.md)
- [HPC Integration](docs/hpc-integration.md)
- [User Project Layout](docs/user-project-layout.md)
- [Installation](docs/installation.md)
- [Release Checklist](docs/release-checklist.md)
- [Documentation Index](docs/README.md)

## License

MIT
