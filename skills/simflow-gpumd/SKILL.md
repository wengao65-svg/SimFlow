---
name: simflow-gpumd
description: Provide GPUMD/NEP domain assistance for bounded input preparation, static validation, dry-run compute planning, selected output parsing, MLP evidence handoff, and artifact recording. Use when Codex works with GPUMD, NEP, run.in, model.xyz, nep.in, train.xyz, test.xyz, nep.restart, nep.txt, loss.out, thermo.out, neighbor.out, GPUMD transport outputs, GPUMDkit-adjacent evidence, or GPUMD/NEP-related SimFlow handoff; do not use it to claim real execution or HPC submission without approval gates.
---

# SimFlow GPUMD

`simflow-gpumd` is a bounded domain assistant for both NEP trainer evidence and
GPUMD MD evidence. It is not a central workflow executor. It owns
software-specific files, commands, outputs, version-sensitive behavior, and
troubleshooting, while `simflow-mlp` owns cross-provider dataset, validation,
active-learning, and production-readiness methodology. This skill does not redefine general MLP production-readiness criteria.

GPUMD and NEP are helper-supported engines for input preparation, static
validation, dry-run planning, selected output parsing, manifest generation,
orchestration reports, and evidence handoff. Real local execution, remote
execution, and HPC submit remain safety-gated and are not performed by this
skill.

Domain Assistant is the Skill product role. The shared capability contract
separately defines GPUMD/NEP helper support, and
`simflow.helper_evidence.v1` is only the output format used by optional helper
scripts. Helper-evidence output does not make this Skill a limited evidence
helper or redefine its GPUMD/NEP domain ownership.

## Trigger conditions

- User mentions GPUMD, NEP, `run.in`, `model.xyz`, `nep.in`, `train.xyz`, `test.xyz`, `nep.restart`, `nep.txt`, `loss.out`, `thermo.out`, `neighbor.out`, GPUMD transport outputs, or GPUMDkit-related evidence.
- User needs to distinguish NEP from-scratch training, ordinary
  checkpoint/restart, foundation-model fine-tuning, or optional community
  two-step training evidence.
- A modeling, computation, analysis_visualization, writing, or handoff task needs GPUMD/NEP-specific file recognition or provenance checks.
- User asks to prepare bounded GPUMD/NEP inputs, validate calculation directories, build dry-run plans, inspect existing files, summarize selected outputs, prepare evidence manifests, or package handoff notes.

## Input conditions

- Existing GPUMD/NEP calculation directory, input files, output files, user command strings, environment notes, artifact ids, or previous checkpoint.
- Optional user-provided GPUMD/NEP version, official-doc source, parser preference, expected evidence role, dataset lineage, or downstream MLP handoff target.
- Unknown GPUMD-family files, commands, or output tables should be recorded with explicit uncertainty instead of forced into a supported parser path.
- For ambiguous requests, clarify whether the user wants input preparation, validation, dry-run planning, selected output parsing, handoff, or real execution. Real execution and submit requests must pass SimFlow approval gates and must not be performed by this skill.

## Output artifacts

- Optional generated `run.in`, `model.xyz`, `nep.in`, input manifest, validation report, dry-run compute plan, selected output parsing summary, helper-run manifest, MLP evidence handoff JSON, warning report, or handoff note.
- Artifact metadata should record source files, hashes when available, command strings as user-provided facts, tool support level, capability support level, assumptions, parser limitations, environment notes, and lineage.
- Output parsing summaries must identify file shape and extracted scalar/table facts without claiming model quality, convergence, or production readiness unless independent validation evidence is present.
- Supported helper capabilities include input generation (`input_generation`), input validation (`input_validation`), compute planning (`compute_planning`), orchestration (`orchestration`), static input inspection (`static_input_inspection`), manifest generation (`manifest_generation`), selected output parsing (`selected_output_parsing`), and evidence handoff (`evidence_handoff`).

## Status write rules

- Read `.simflow/state/` before acting when workflow state is relevant, and resolve explicit `project_root` before writing `.simflow/` reports, artifacts, checkpoints, or helper-run manifests.
- Helper outputs are pure evidence producers by default. They may write
  requested manifests, reports, or bounded inputs under `project_root`, but
  they do not initialize or advance stages, do not register artifacts, and do
  not create checkpoints unless explicit helper-run recording is requested.
- Default helper report paths live under project-root `reports/<engine>/`.
  `.simflow` is touched only by explicit helper-run recording.
- `--record-helper-run` is `record_only`: it records helper evidence and
  lineage only. Canonical stage runners own stage transitions, and
  checkpoint/state-admin APIs own checkpoint operations.
- Direct helpers do not register arbitrary report artifacts. Canonical stage
  runners may ingest/register outputs when the workflow stage owns them.
- Keep real execution and submit separate from helper support. `gpumd` and `nep` helper support covers input preparation, static validation, dry-run planning, manifest generation, selected output parsing, orchestration reports, and evidence handoff.
- Use open stages such as `computation`, `analysis_visualization`, or `writing` according to research intent. GPUMD/NEP task labels are recipe/helper metadata, not top-level workflow stages.
- Do not write under `.omx/`; it belongs to the host session, not SimFlow workflow state.

## Working procedure

1. Classify the request as input preparation, validation, dry-run planning, static inspection, manifest generation, selected output parsing, troubleshooting, writing, or handoff.
2. Load `references/gpumd_official_sources.md` for documentation navigation, `references/gpumd_file_map.md` for file recognition and generic MLP evidence-role mapping, `references/gpumd_static_inspection.md` for input checks, and `references/gpumd_selected_output_parsing.md` for parser limits.
3. Load `references/gpumd_nep_evidence.md` for NEP training modes and model evidence, `references/gpumd_task_checklists.md` for task checks, and `references/gpumd_troubleshooting.md` for common diagnosis only when the request needs them.
4. Load `references/gpumd_nep_community_methodology.md` only for cleaned,
   community-derived NEP/GPUMD methodology or troubleshooting claims. Keep
   official facts, stable methodology, version-sensitive notes, and unresolved
   claims distinct.
5. Inspect existing local files before interpreting outputs. Report missing files and ambiguous semantics instead of inventing input contents or execution results.
6. Delegate cross-provider data coverage, validation design, active-learning
   readiness, and production MLP-MD readiness to `simflow-mlp`; retain
   GPUMD/NEP file semantics and provider implementation details here.
7. Use the optional helper scripts only for offline preparation, validation, planning, parsing, and evidence tasks. They must not call `gpumd`, `nep`, NEPTrainKit, GPU tools, MPI, schedulers, or remote systems.
8. Register generated reports or helper-run manifests as artifacts only when explicit helper-run recording is requested or when a canonical stage runner ingests those outputs.

## Reference map

- `references/gpumd_official_sources.md`: Official GPUMD/NEP documentation entry points.
- `references/gpumd_file_map.md`: Common input/output files and evidence roles.
- `references/gpumd_static_inspection.md`: Static input inspection checks for existing files.
- `references/gpumd_selected_output_parsing.md`: Narrow output parsing scope and limits.
- `references/gpumd_nep_evidence.md`: NEP dataset, model, and training evidence.
- `references/gpumd_nep_community_methodology.md`: Cleaned community-derived
  NEP/GPUMD methodology, version-sensitive notes, and unresolved claims.
- `references/gpumd_task_checklists.md`: Task-oriented review checklists.
- `references/gpumd_troubleshooting.md`: Failure and uncertainty diagnosis.

## Optional helper scripts

- `scripts/generate_gpumd_inputs.py`: Generate bounded GPUMD/NEP input files from explicit structure, potential/model, dataset, and parameter evidence.
- `scripts/validate_gpumd_inputs.py`: Statically validate GPUMD/NEP inputs without running the engine.
- `scripts/orchestrate_gpumd_task.py`: Build SimFlow reports, dry-run compute plans, handoff records, and optional helper-run evidence without submitting jobs.
- `scripts/inspect_gpumd_inputs.py`: Inspect existing GPUMD/NEP inputs without running anything.
- `scripts/build_gpumd_manifest.py`: Build a provenance manifest from existing files, commands, versions, hashes, and environment notes.
- `scripts/parse_gpumd_outputs.py`: Parse selected recognized table-like outputs conservatively.
- `scripts/prepare_gpumd_handoff.py`: Package existing GPUMD/NEP evidence into a handoff summary.

These helpers are optional routes, not the only valid parser, report format, or analysis path. User scripts, official documentation, GPUMDkit, notebooks, shell commands, or custom Python are acceptable when evidence, lineage, assumptions, and risks are recorded.

## Checkpoint rules

- GPUMD/NEP helpers do not create stage-boundary checkpoints by default.
- Helper-run recording remains `record_only`; use canonical stage runners or
  checkpoint/state-admin APIs when checkpoint operations are explicitly needed.
- For real execution or submit requests without approval evidence, keep
  workflow state waiting and report the missing approval gate; do not record a
  completed calculation or job.

## Prohibited actions

- Do not expose GPUMD/NEP real execution, local submit, remote execution, or HPC submit as helper-supported actions.
- Do not run `gpumd`, `nep`, NEPTrainKit, GPU profilers, MPI launchers, schedulers, or remote commands from this skill.
- Do not claim model quality, convergence, transferability, thermal conductivity, transport properties, or production readiness without explicit evidence.
- Do not replace `simflow-mlp` readiness criteria with GPUMD/NEP-specific file
  presence, loss values, fixed parameter recommendations, or community rules.
- Do not present community-derived NEP two-step training as required for NEP
  or as a general method for MACE, DeePMD, NequIP, Allegro, or other trainers.
- Do not fabricate GPUMD/NEP results, datasets, figures, citations, completed calculations, or validation status.
- Do not record unfinished or failed calculations as completed results.

## Manual confirmation scenarios

- The user requests real local, remote, or HPC execution; scheduler interaction; dependency installation; or GPU resource use.
- Existing files would be overwritten, converted destructively, or interpreted beyond available evidence.
- Dataset ownership, proprietary potentials, credentials, licensed files, or private paths may be exposed.
- Validation criteria, active-learning thresholds, or production MLP-MD readiness affect a scientific conclusion.
