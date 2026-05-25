# SimFlow Developer Guide

## Architecture Overview

SimFlow is a plugin-hosted workflow layer, not a standalone research executor.
Codex, Claude Code, or another host agent performs the scientific work. SimFlow
records evidence, state, lineage, checkpoints, gates, and handoff context.

```text
User request
  -> SimFlow skills
  -> workflow-layer contracts
  -> MCP recording tools
  -> optional runtime helpers
  -> .simflow/ project state
```

## Directory Structure

```text
skills/          canonical skill entry points and domain helpers
workflow/        stages, recipes, gates, policies
mcp/             recording and bounded helper servers
runtime/         core facades and optional helpers
schemas/         JSON schemas
tests/           unit, MCP, workflow, skill, and e2e tests
docs/            design and user documentation
scripts/         packaging, marketplace, scaffold, and validation scripts
```

New behavior should use `workflow/recipes/`, canonical stages, and helper
modules under `runtime/simflow_helpers/`.

## Design Rules

### Skill-First

User-facing research work enters through canonical skills. Skills describe
trigger conditions, evidence requirements, risks, safety boundaries, and
handoff needs. They must not require one parser, one builder, one report
filename, or one software package as the only valid path.

### Open Stage Model

Canonical stages are:

```text
literature_review
proposal
modeling
computation
analysis_visualization
writing
```

`input_generation` belongs inside `computation`; `visualization` belongs inside
`analysis_visualization`; review is a cross-stage checking action.

### State In .simflow/

All workflow state is written under the user's project `.simflow/` root. MCP
write tools must receive explicit `project_root`; plugin root and project root
must not be conflated.

### Optional Helpers

Runtime parsers, validators, templates, and engine helpers are optional. They
may suggest, inspect, validate, or record artifacts. They should not decide the
science or block reasonable unlisted workflows.

### Evidence-Based Gates

Real local, remote, or HPC execution requires dry-run evidence, validation,
credential scan, resource estimate, matching hashes, and an approval reference.
Boolean-only approval is not enough.

## Adding A Skill

1. Run `node scripts/scaffold_skill.js my-new-skill`.
2. Edit `skills/my-new-skill/SKILL.md`.
3. Keep the body focused on trigger conditions, evidence, risks, safety, and
   handoff.
4. Add tests if the skill introduces new contract language.
5. Run `npm run validate:skills`.

Do not add a skill that acts as a mandatory workflow executor.

## Adding A Helper

Helpers should be bounded and optional. A good helper records what it did:

- script or command
- input artifacts
- output artifacts
- environment assumptions
- lineage links
- warnings and uncertainty

For analysis helpers, self-written Python and external scientific libraries are
valid paths when they are recorded with the same evidence discipline.

## Running Verification

```bash
python -m pytest tests/ -q
npm run validate:all
```

If marketplace or distribution files change, also run the marketplace build and
validation commands documented in the release workflow.
