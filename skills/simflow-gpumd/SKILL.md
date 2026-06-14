---
name: simflow-gpumd
description: Provide limited GPUMD/NEP domain assistance for static input inspection, provenance manifest generation, selected output parsing, MLP evidence handoff, and artifact recording. Use when Codex works with GPUMD, NEP, run.in, model.xyz, nep.in, train.xyz, test.xyz, nep.txt, loss.out, thermo.out, GPUMD transport outputs, GPUMDkit-adjacent evidence, or GPUMD/NEP-related SimFlow handoff; do not use it to claim helper-supported GPUMD/NEP execution, input generation, or HPC submission.
---

# SimFlow GPUMD

`simflow-gpumd` is a limited domain assistant for GPUMD and NEP evidence. It is not a central workflow executor and does not make GPUMD or NEP tool-level helper-supported software in SimFlow. Treat `gpumd` and `nep` as tracked-only tools with helper-supported capabilities only for static inspection, manifest generation, selected output parsing, and evidence handoff.

## Trigger conditions

- User mentions GPUMD, NEP, `run.in`, `model.xyz`, `nep.in`, `train.xyz`, `test.xyz`, `nep.txt`, `loss.out`, `thermo.out`, GPUMD transport outputs, or GPUMDkit-related evidence.
- A modeling, computation, analysis_visualization, writing, or handoff task needs GPUMD/NEP-specific file recognition or provenance checks.
- User asks to inspect existing GPUMD/NEP files, summarize selected outputs, prepare evidence manifests, or package handoff notes.

## Input conditions

- Existing GPUMD/NEP calculation directory, input files, output files, user command strings, environment notes, artifact ids, or previous checkpoint.
- Optional user-provided GPUMD/NEP version, official-doc source, parser preference, expected evidence role, dataset lineage, or downstream MLP handoff target.
- Unknown GPUMD-family files, commands, or output tables should be recorded with explicit uncertainty instead of forced into a supported parser path.
- For ambiguous requests, clarify whether the user wants static inspection, manifest generation, selected output parsing, or handoff. Real execution, input generation, and submit requests must return or preserve a `capability_warning` and be routed to generic tracked-only evidence and approval gates rather than this helper as supported execution.

## Output artifacts

- Optional static input inspection report, GPUMD/NEP file manifest, selected output parsing summary, helper-run manifest, MLP evidence handoff JSON, warning report, or handoff note.
- Artifact metadata should record source files, hashes when available, command strings as user-provided facts, tool support level `tracked_only`, capability support level, assumptions, parser limitations, environment notes, and lineage.
- Output parsing summaries must identify file shape and extracted scalar/table facts without claiming model quality, convergence, or production readiness unless independent validation evidence is present.

## Status write rules

- Read `.simflow/state/` before acting when workflow state is relevant, and resolve explicit `project_root` before writing `.simflow/` reports, artifacts, checkpoints, or helper-run manifests.
- Keep `gpumd` and `nep` as tool-level `tracked_only`; capability-level helper support covers only `static_input_inspection`, `manifest_generation`, `selected_output_parsing`, and `evidence_handoff`.
- Use open stages such as `computation`, `analysis_visualization`, or `writing` according to research intent. GPUMD/NEP task labels are recipe/helper metadata, not top-level workflow stages.
- Do not write under `.omx/`; it belongs to the host session, not SimFlow workflow state.

## Working procedure

1. Classify the request as static inspection, manifest generation, selected output parsing, troubleshooting, writing, or handoff.
2. Load `references/gpumd_official_sources.md` for documentation navigation, `references/gpumd_file_map.md` for file recognition, `references/gpumd_static_inspection.md` for input checks, and `references/gpumd_selected_output_parsing.md` for parser limits.
3. Load `references/gpumd_nep_evidence.md` for NEP training/model evidence, `references/gpumd_task_checklists.md` for task checks, and `references/gpumd_troubleshooting.md` for common diagnosis only when the request needs them.
4. Inspect existing local files before interpreting outputs. Report missing files and ambiguous semantics instead of inventing input contents or execution results.
5. Use the optional helper scripts only for offline evidence tasks. They must not call `gpumd`, `nep`, NEPTrainKit, GPU tools, MPI, schedulers, or remote systems.
6. Register generated reports or helper-run manifests as artifacts with lineage when writing SimFlow state.

## Reference map

- `references/gpumd_official_sources.md`: Official GPUMD/NEP documentation entry points.
- `references/gpumd_file_map.md`: Common input/output files and evidence roles.
- `references/gpumd_static_inspection.md`: Static input inspection checks for existing files.
- `references/gpumd_selected_output_parsing.md`: Narrow output parsing scope and limits.
- `references/gpumd_nep_evidence.md`: NEP dataset, model, and training evidence.
- `references/gpumd_task_checklists.md`: Task-oriented review checklists.
- `references/gpumd_troubleshooting.md`: Failure and uncertainty diagnosis.

## Optional helper scripts

- `scripts/inspect_gpumd_inputs.py`: Inspect existing GPUMD/NEP inputs without generating or running anything.
- `scripts/build_gpumd_manifest.py`: Build a provenance manifest from existing files, commands, versions, hashes, and environment notes.
- `scripts/parse_gpumd_outputs.py`: Parse selected recognized table-like outputs conservatively.
- `scripts/prepare_gpumd_handoff.py`: Package existing GPUMD/NEP evidence into a handoff summary.

These helpers are optional routes, not the only valid parser, report format, or analysis path. User scripts, official documentation, GPUMDkit, notebooks, shell commands, or custom Python are acceptable when evidence, lineage, assumptions, and risks are recorded.

## Checkpoint rules

- Create a checkpoint only when GPUMD/NEP evidence is ready for review, handoff, or an approval gate.
- Create failure checkpoints for true helper failures such as unreadable evidence, parse failure, unavailable proprietary files, or blocked approval gates.
- For unsupported execution or input-generation requests, return a `capability_warning` and keep workflow state waiting; do not record a completed or failed checkpoint solely for the unsupported capability.

## Prohibited actions

- Do not mark GPUMD or NEP as tool-level helper-supported software.
- Do not expose GPUMD/NEP real execution, local submit, remote execution, HPC submit, or input generation as helper-supported capabilities.
- Do not run `gpumd`, `nep`, NEPTrainKit, GPU profilers, MPI launchers, schedulers, or remote commands from this skill.
- Do not generate production GPUMD/NEP inputs or claim model quality, convergence, transferability, thermal conductivity, transport properties, or production readiness without explicit evidence.
- Do not fabricate GPUMD/NEP results, datasets, figures, citations, completed calculations, or validation status.
- Do not record unfinished or failed calculations as completed results.

## Manual confirmation scenarios

- The user requests real local, remote, or HPC execution; scheduler interaction; dependency installation; or GPU resource use.
- Existing files would be overwritten, converted destructively, or interpreted beyond available evidence.
- Dataset ownership, proprietary potentials, credentials, licensed files, or private paths may be exposed.
- Validation criteria, active-learning thresholds, or production MLP-MD readiness affect a scientific conclusion.
