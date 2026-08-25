# Skill Design

## Purpose

SimFlow Skills constrain how the host agent approaches computational research.
They are reusable instruction bundles, not workflow executors or runtime user
manuals.

The architecture separates three concerns:

```text
Research Task Skill  -> how to do the current class of work well
Domain Skill         -> what is specific to an engine or method
SimFlow Runtime      -> what actually happened and what must be safeguarded
```

## Public Skill Set

The public surface contains one opt-in Framework Skill, seven Research Task
Skills, and five Domain Skills. See `skills/README.md` for the complete list.
Host agents discover and compose these Skills directly from their metadata.

Operational concerns are not Skills:

- safety policy is enforced by runtime;
- checkpoints and recovery are persistence operations;
- handoff is state summarization/serialization;
- scientific verification lives in Task/Domain minimum checks;
- execution truth, hashes, file existence, and job status live in runtime.

Unsupported engines do not receive placeholder Skills.

## Pure Skill Contract

Research Task Skills use this structure:

```text
Purpose
Use when
Do not use when
Task principles
Minimum checks
Common failure modes
Escalate uncertainty when
Completion criteria
Optional references
```

Domain Skills use the same structure with `Domain principles`.

Task and Domain Skills may guide, inspect, suggest, and use host tools. They
must not:

- require MCP engagement;
- own workflow stage transitions;
- register artifacts or create checkpoints as completion conditions;
- decide approval or real execution status;
- enforce a project directory layout;
- require one parser, builder, helper, report name, or software path.

Removing every SimFlow MCP tool should not remove the scientific value of a
Task or Domain Skill.

## Rule Admission

Keep the main `SKILL.md` focused on behavior the agent is likely to get wrong.
A rule belongs in the main Skill only when at least one condition applies:

1. the failure has appeared in real sessions;
2. the behavior is high risk and models commonly repeat it;
3. omitting the rule materially weakens the completion criteria.

Detailed methods, examples, parameter discussions, and long checklists belong
under `references/`. Optional bounded utilities belong under `scripts/`.

## Framework And Composition Contract

The `simflow` Framework Skill is explicit and opt-in. It supplies project-memory,
provenance, recovery, recording, and execution-safety semantics; it does not
select or route other Skills.

Host agents own discovery and composition. They should load the smallest set of
Skills that materially improves the request, without a numeric limit. Multiple
Task or Domain Skills are valid when a request spans their responsibilities.
User-selected Skills take priority, and current intent matters more than cwd,
phase, or directory names.

Host-native custom Skills may participate in composition. SimFlow does not
provide a custom-Skill registry, binding schema, override mechanism, or
`.simflow/extensions/skills` directory.

## Domain Skill Pattern

Domain Skills answer questions such as:

- Which files and engine-specific semantics matter?
- Which input combinations are inconsistent?
- Which warnings and failure modes are common?
- Which official references or optional tools are useful?
- Which uncertainty must be surfaced rather than defaulted?

Domain Skill, helper support level, and helper-evidence format are separate
concepts. `workflow/toolchains/capabilities.json` remains the support-level
source of truth.

## Helper Contract

Helpers are optional scientific utilities. Their default behavior is standalone:
they may read user files and write requested outputs inside the user-authorized
project path without initializing SimFlow state.

If a caller explicitly requests runtime recording, that behavior belongs to a
shared runtime adapter rather than the Skill contract. Helpers must remain
usable when recording is unavailable.

## Validation

Skill validation checks:

- the correct pure contract sections;
- no mandatory MCP lifecycle language;
- no artifact/checkpoint/stage ownership;
- no fixed helper or report requirement;
- no unsupported engine capability claim;
- host-native discovery without central routing or cardinality limits;
- explicit-only Framework invocation on hosts that support it.
