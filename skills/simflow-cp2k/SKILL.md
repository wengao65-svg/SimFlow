---
name: simflow-cp2k
description: Provide CP2K domain assistance for official-documentation lookup, input preparation, validation, dry-run planning, troubleshooting, output parsing, analysis/visualization, and artifact recording. Use when Codex works with CP2K, CP2K input decks, GLOBAL, FORCE_EVAL, DFT, MGRID, SCF, QS, KIND, MOTION, ENERGY, GEO_OPT, CELL_OPT, MD/AIMD, restart files, .log, .ener, trajectories, basis/potential choices, cutoff convergence, or CP2K-related SimFlow handoff.
---

# SimFlow CP2K

`simflow-cp2k` is a domain assistant. It helps the host agent use CP2K official documentation, portable example patterns, SimFlow state, helper scripts, optional user-provided CP2K source-tree evidence, and conservative scientific checks. It is not a central workflow executor and does not define the full CP2K capability surface.

## Trigger conditions

- User mentions CP2K, CP2K input decks, `.inp`, `.xyz`, `.cif`, `.log`, `.out`, `.ener`, restart files, trajectories, `GLOBAL`, `FORCE_EVAL`, `DFT`, `MGRID`, `SCF`, `QS`, `KIND`, `MOTION`, `ENERGY`, `GEO_OPT`, `CELL_OPT`, `MD`, AIMD, continuation, troubleshooting, or parsing.
- A modeling, computation, analysis, visualization, writing, or handoff task needs CP2K-specific context.
- User asks to inspect, prepare, validate, troubleshoot, parse, analyze, visualize, or hand off CP2K-related artifacts.

## Input conditions

- User-provided CP2K files, task intent, calculation directory, artifact ids, previous checkpoint, or user-selected script/tool.
- Optional CP2K version, executable hint, user-provided source-tree path, parser preference, template, external tool, or custom analysis path.
- Unknown or advanced CP2K tasks should return uncertainty, candidates, and missing information instead of being forced into `ENERGY`.
- For ambiguous setup, clarify at least calculation intent, available predecessors, structure/source files, charge/multiplicity, periodicity/cell, basis/potential family, target accuracy, ensemble/thermostat/barostat when relevant, restart semantics, and whether any real execution is requested.

## Output artifacts

- Optional input manifest, validation report, compute-plan note, analysis/troubleshooting report, restart metadata, or handoff note.
- Optional official-source note, example-pattern note, figure/caption, reproducibility note, or helper-run manifest when using SimFlow helpers, custom Python, notebooks, shell tools, CP2K tools, or user scripts.
- Artifact metadata should record source files, command/tool choice, parameters, assumptions, task uncertainty, environment, hashes when available, official URLs or user-provided source paths, and lineage.

## Status write rules

- Resolve explicit `project_root` before writing `.simflow/` state, artifacts, checkpoints, reports, or lineage.
- Read `.simflow/state/` before acting and write CP2K reports only as evidence records; do not automatically impose a fixed CP2K stage progression.
- Helper outputs are pure evidence producers by default. They may write
  requested CP2K inputs or reports under `project_root`, but they do not
  initialize or advance stages, do not register artifacts, and do not create
  checkpoints unless explicit helper-run recording is requested.
- Default helper report paths live under project-root `reports/<engine>/`.
  `.simflow` is touched only by explicit helper-run recording.
- `--record-helper-run` is `record_only`: it records helper evidence and
  lineage only. Canonical stage runners own stage transitions, and
  checkpoint/state-admin APIs own checkpoint operations.
- Direct helpers do not register arbitrary report artifacts. Canonical stage
  runners may ingest/register outputs when the workflow stage owns them.
- Use open stages such as `modeling`, `computation`, or `analysis_visualization` according to research intent.
- Keep CP2K task labels such as `dft`, `aimd`, `geo_opt`, `cell_opt`, `restart`, `qmmm`, `neb`, `xtb`, or `custom` separate from workflow stage.
- Do not write under `.omx/`; it belongs to the host session, not SimFlow workflow state.

## Working procedure

1. Read `.simflow/state/` before acting and resolve `project_root` explicitly before any SimFlow write.
2. Classify the request as official-source lookup, input preparation, validation, dry-run planning, troubleshooting, parsing, analysis/visualization, writing, or handoff. Return uncertainty when the task does not match a known safe pattern.
3. Prefer official CP2K sources for parameter or workflow claims. Before official CP2K parameter or keyword lookup, first load `references/cp2k_official_sources.md` and use its official links in latest-first or version-matched order; do not run a generic web search first to decide whether a CP2K keyword exists. Load `references/cp2k_example_patterns.md` for portable setup and execution-environment boundary patterns, `references/cp2k_task_checklists.md` for task-specific checks, `references/cp2k_parameters.md` for parameter policies, and `references/cp2k_troubleshooting.md` for diagnosis. Load `references/cp2k_local_examples_index.md` only when the user provides a CP2K source-tree path or relevant environment variable.
4. Load only the reference files needed for the concrete request. Avoid loading all CP2K references unless the user asks for a broad CP2K workflow audit.
5. Inspect local inputs before generating or interpreting results. Preserve user-provided files and report missing predecessors instead of inventing them.
6. Default compute work to dry-run/static inspection. Real local, remote, or HPC execution requires the same approval gate evidence used by `simflow-computation`.
7. Register outputs as artifacts with metadata and lineage only when explicit helper-run recording is requested or when a canonical stage runner ingests those outputs.

## Reference map

- `references/cp2k_official_sources.md`: Official CP2K manual, howto, exercises, source-tree docs, and local documentation navigation.
- `references/cp2k_example_patterns.md`: Portable CP2K calculation-directory patterns for static DFT, cutoff convergence, optimization, AIMD, restart, output review, and execution handoff.
- `references/cp2k_task_checklists.md`: ENERGY, GEO_OPT, CELL_OPT, AIMD, restart, parsing, and advanced/custom checklist guidance.
- `references/cp2k_parameters.md`: Common CP2K parameter policy for `GLOBAL`, `FORCE_EVAL`, `DFT`, `MGRID`, `SCF`, `QS`, `XC`, `SUBSYS`, `KIND`, `MOTION`, and restart sections.
- `references/cp2k_troubleshooting.md`: Convergence, cutoff, MD drift, restart, missing basis/potential, and output parsing diagnosis.
- `references/cp2k_local_examples_index.md`: Optional user-provided CP2K source-tree documentation, tests, benchmarks, and data-source navigation; not needed for ordinary setup review or execution-environment planning.
- `references/cp2k_methods_index.md` and `references/cp2k_common_workflows.md`: Lightweight legacy indexes for the helper-supported common-task layer.

## Recommended checks

- Input set: CP2K input deck and referenced coordinate, restart, basis, potential, topology, or force-field files are present and mutually consistent for the requested task.
- Structure: element symbols, atom counts, cell vectors or ABC values, periodicity, coordinate format, charge/multiplicity, and `KIND` coverage are explicit.
- DFT setup: `FORCE_EVAL/METHOD`, `DFT`, `BASIS_SET_FILE_NAME`, `POTENTIAL_FILE_NAME`, `QS`, `MGRID`, `SCF`, `XC`, and all `KIND` basis/potential assignments are traceable to official docs or local libraries.
- Grid and SCF: `CUTOFF`, `REL_CUTOFF`, `EPS_DEFAULT`, `EPS_SCF`, `MAX_SCF`, OT/diagonalization, mixing, smearing, and restart guesses match the system and accuracy goal.
- Motion: `RUN_TYPE` agrees with `MOTION/GEO_OPT`, `MOTION/CELL_OPT`, or `MOTION/MD`; geometry/cell optimization thresholds, constraints, ensemble, timestep, thermostat/barostat, output frequencies, and restart policy are explicit.
- Predecessors: restarts have compatible restart artifacts; continuation has clear semantics; parsing/troubleshooting has logs and available `.ener`, trajectory, and restart files; advanced workflows have user-provided method intent.
- Outputs: convergence, warnings, final energy, forces/stress when available, MD temperature/conserved quantity, final structure, restart metadata, and figure lineage are traceable to inputs and commands.
- Reproducibility: CP2K version, executable family, manual/source version, basis/potential file names, relevant environment/module information, helper versions, and source URLs or user-provided source-tree paths are recorded when available.
- Execution environment boundary: do not assume the current workspace has CP2K, MPI, modules, or the same basis/potential library paths as the execution target. When execution is expected elsewhere, prepare transferable calculation directories, manifests, and dry-run command plans after the SimFlow approval gate.

## Optional helper scripts

- `scripts/generate_cp2k_inputs.py`: Generate conservative common-task CP2K input decks and normalized coordinates for `energy`, `geo_opt`, `cell_opt`, `aimd_nvt`, `aimd_nve`, and `aimd_npt` from CIF or XYZ structures. It covers a limited DFT/QS/MOLOPT/GTH-style surface and may require explicit `element_params` beyond its built-in element defaults.
- `scripts/validate_cp2k_inputs.py`: Statically inspect common-task input decks for `GLOBAL/RUN_TYPE`, `FORCE_EVAL/DFT`, basis/potential file names, `MGRID`, `SCF`, `OT`, `XC`, `SUBSYS/CELL`, topology coordinates, `KIND` coverage, task-motion consistency, and restart file presence.
- `scripts/parse_cp2k_outputs.py`: Parse available `.log`, `.ener`, `*-pos-*.xyz`, and `.restart` files into an analysis report without running CP2K.
- `scripts/orchestrate_cp2k_task.py`: Build SimFlow CP2K reports, dry-run compute plans, handoff records, and optional helper-run evidence for common tasks without submitting jobs.

These helpers are optional domain tools, not the only valid parser, builder, analysis path, or report format. Official CP2K examples, user inputs, CP2K tools, ASE, notebooks, shell commands, or custom Python are acceptable when evidence, lineage, assumptions, and risks are recorded.

## Checkpoint rules

- CP2K helpers do not create stage-boundary checkpoints by default.
- Helper-run recording remains `record_only`; use canonical stage runners or
  checkpoint/state-admin APIs when checkpoint operations are explicitly needed.

## Prohibited actions

- Do not default unknown CP2K tasks to `ENERGY`.
- Do not claim to replace the CP2K manual or cover the entire CP2K parameter space.
- Do not require built-in CP2K parsers, generated templates, fixed report names, or common-task aliases as the only valid path.
- Do not copy CP2K basis libraries, potential libraries, benchmark trees, credentials, proprietary force-field files, local installation paths, maintainer-private paths, or large local source-tree content into reports or distributable skill docs.
- Do not fabricate CP2K results, literature, figures, citations, convergence status, or completed calculations.
- Do not record unfinished or failed calculations as completed results.
- Do not submit real local, remote, or HPC jobs from this skill without the relevant approval gate.

## Manual confirmation scenarios

- Restart semantics, ensemble, thermostat/barostat, cell setup, charge/multiplicity, force field/basis/potential choice, cutoff/SCF standard, or advanced method scope is ambiguous.
- Real execution, remote systems, licensed/proprietary files, credentials, destructive operations, or high-cost resources are involved.
- Existing user files would be overwritten or interpreted beyond available evidence.
- The requested analysis method would materially affect a scientific conclusion, figure, or manuscript claim.
