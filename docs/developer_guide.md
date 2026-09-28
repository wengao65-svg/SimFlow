# SimFlow Developer Guide

SimFlow is a portable set of 12 scientific Skills. The host agent applies the
relevant Research Task and Domain Skills, and the user owns research choices,
experiment records, and authorization of concrete execution. See
[the direction plan](direction-skill-pack.md) for the research and migration
decisions behind this boundary.

## Skill layout

Each Skill lives directly under `skills/<name>/` and has `SKILL.md`. Keep the
main instructions short: triggering context, key scientific checks, failure
cases, claim limits, and completion criteria. Put detailed methods in
`references/`. Optional Python tools belong to that Skill's `scripts/`, local
code to its `lib/`, and fixed templates to `assets/`. A Skill must work when
installed alone; it must not import files from another SimFlow Skill or from
the source repository root.

Task and Domain Skills guide the agent. They do not route one another, own
stage transitions, create a project ledger, initialize `.simflow/`, or certify
that execution was approved or scientifically successful.

## Helper behavior

Scripts should do bounded scientific work: inspect inputs, validate parameters,
parse outputs, transform structures, prepare text, or draw figures. Pure checks
print JSON to stdout. A report is written only when the caller names a path;
generation tools require an explicit destination. Existing calculation inputs
must not be overwritten silently. Do not add helper-run records, generic file
hashes, stage state, approval gates, or registry updates.

Use only the source evidence needed for the scientific operation. A parser's
success means it parsed selected fields; it does not prove convergence, job
completion, or model quality. Preserve restricted POTCAR and credential
boundaries. Real local, remote, or scheduler execution belongs to the host and
the user's authorization for the concrete action.

## Checks

```bash
python scripts/audit_skill_pack.py --strict
python -m pytest tests/ -q
npm run validate:all
SIMFLOW_RELEASE_ALLOW_DIRTY=1 npm run validate:release
```

Distribution tests build Codex, Claude Code, and OpenCode packages and run the
installed Python entrypoints from outside this checkout. Keep all three
builders aligned when changing Skill files or resources.
