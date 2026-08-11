# Workflow Layer Design

## Positioning

SimFlow provides research guidance and a small event-driven runtime around
computational work. It is not a centralized executor, mandatory DAG, or stage
state machine. Its compact Experiment notebooks preserve scientific intent
across requests without turning host sessions into workflow state.

## Research Stages

The canonical vocabulary is:

1. `literature_review`
2. `proposal`
3. `modeling`
4. `computation`
5. `analysis_visualization`
6. `writing`

Stage definitions describe intent, acceptable evidence, suggested checks,
risks, and approval triggers. They are advisory contracts. Any stage may be
used independently, revisited, skipped, or combined with custom work when the
scientific inputs are adequate.

Task Skill selection follows the user's immediate intent, not the current
stage or directory. For example, explaining an RDF inside a computation folder
uses analysis guidance; preparing a missing calculation from an analysis folder
uses computation guidance.

## Recipes

DFT, AIMD, classical MD, MLP-MD, phonon, NEB, defects, adsorption, and custom
paths are recipes or tags. They offer typical evidence and risk guidance, not
software admission rules or executor graphs. Unknown software remains valid
context and does not get silently mapped to a supported engine.

## Hard Constraints

Only safety and truth boundaries are hard:

- real local, remote, or scheduler execution needs a validated immutable run
  plan and approval bound to its hash;
- credentials and restricted content are not persisted;
- writes stay inside explicit `project_root`;
- unfinished calculations are not recorded as completed;
- literature, data, figures, job status, and scientific claims are not
  fabricated;
- legacy state and project directories are not rewritten automatically.

## Runtime Policies

Current policy contracts cover:

- one read-only Experiment re-entry inspection per project per user request;
- append-only scientific memory with exact files retained as evidence;
- immutable dry-run planning before real execution;
- approval for real execution with approval reuse only for unchanged plans;
- logical event recording rather than per-file registration;
- compact checkpoints at actual recovery boundaries;
- independent stage entry;
- credential exclusion.

Ordinary task or stage completion does not require a checkpoint. Producing a
file does not automatically require a record or semantic artifact version.
Material-action pairing applies only to persistent changes in evidence or
recoverability, not ordinary parameter edits.

## Handoff

Handoff is a host summary, not a mandatory workflow action. A useful handoff
states the current goal, active or recent runs, meaningful deliverables,
recoverable checkpoints, risks, next action, and approval needs. Persist it
only when the user or project needs a durable report. Cross-request scientific
memory belongs in the relevant Experiment notebook, not in an automatic handoff
or host transcript import.
