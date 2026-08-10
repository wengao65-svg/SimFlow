---
name: simflow-lammps
description: Provide LAMMPS domain assistance for setup, validation, MLP-MD deployment, output intake, troubleshooting, and traceable artifacts.
---

## Cross-Session Experiment Memory

For work inside an existing user project, call `simflow_state/project_reentry` with the explicit canonical `project_root` before inspecting project files or performing work. Do not read or import host session transcripts as normal project memory. If the forward-only ledger has not started, call `begin_experiment` before new tracked work. Call `start_activity` before every project mutation, computation, analysis, transfer, or state change, and call `finish_activity` with outputs, outcome, failure/recovery details, and `next_action` afterward. Once the ledger is enabled, linked SimFlow writes must carry `session_context_id`, `experiment_id`, and `activity_id`. End with `session_handoff` when possible; an unclosed activity is intentionally surfaced as interrupted work on the next re-entry.

`.simflow/memory/ledger.sqlite3` is authoritative; JSON, JSONL, and Markdown files are derived views. Enabled-ledger writes fail closed in the core runtime, including direct runtime/helper calls. Propagate `SIMFLOW_SESSION_CONTEXT_ID`, `SIMFLOW_EXPERIMENT_ID`, optional `SIMFLOW_ITERATION_ID`, and `SIMFLOW_ACTIVITY_ID` to child processes. Treat the ledger as a human-readable electronic lab notebook backed by an immutable provenance DAG, not as a replacement for Git.

# SimFlow LAMMPS

`simflow-lammps` is a LAMMPS domain assistant, not a central workflow executor.
It interprets, checks, and records LAMMPS input/output evidence. Top-level
stages, checkpoints, approval gates, and cross-skill handoff remain owned by
the SimFlow workflow layer.

## Trigger conditions

- The user mentions LAMMPS, input script, data file, log, dump, trajectory,
  force field, RDF, MSD, diffusion, NVE/NVT/NPT/NPH, ReaxFF, DeepMD, MACE,
  NequIP, Allegro, PACE, SNAP, QUIP, or MLP-MD.
- Modeling, computation, analysis_visualization, or writing needs
  LAMMPS-specific file context.
- The user needs to inspect, draft, record, interpret, or hand off LAMMPS files.

## Task Routing

| Route | Use | Main Evidence |
| --- | --- | --- |
| `classic_md` | Classical-potential MD with EAM, MEAM, Tersoff, SW, AIREBO, LJ, KIM, or similar models | Potential source, units, atom_style, ensemble, timestep, log/dump |
| `reactive_md` | Reactive or variable-charge MD such as ReaxFF or COMB | Parameter source, charge equilibration, long-range settings, stability, timestep |
| `mlp_md_deployment` | LAMMPS runs MD with an already trained MLP model | Model file, type mapping, LAMMPS package/build evidence, `simflow-mlp` handoff |
| `analysis_handoff` | LAMMPS log/dump/trajectory output intake before analysis-stage handoff | `lammps_output_intake_manifest`, dump columns, units, atom ids, image flags, type mapping |
| `troubleshooting` | Input, runtime, package, MPI/GPU, or physical-stability problems | Error/warning text, minimal reproducer inputs, environment, change record |

For MLP-MD, this skill's claim scope is **deployment only**: it explains how
LAMMPS references the model and prepares/checks MD inputs. It does not evaluate
MLP training quality, extrapolation safety, validation coverage, or production
readiness. Those evidence questions must be handed to `simflow-mlp`.

Analysis boundary: `simflow-lammps` does not own final property analysis,
statistics, figures, or scientific claims. It records LAMMPS-specific output
semantics and hands analysis intent to `simflow-analysis-visualization`.

## Input conditions

- User-provided data file, input script, log, dump, force-field parameters,
  model-file metadata, `lmp -h` output, artifact id, task intent, or checkpoint.
- Optional tools may include MDAnalysis, OVITO, Pizza.py, self-written Python,
  shell commands, notebooks, or user-specified tools.
- Unknown or unlisted tasks should return candidate routes and missing inputs;
  do not force them into fixed MD aliases.
- Ambiguous intent requires clarification of system, force-field source, units,
  atom style, ensemble, timestep, equilibration/production boundary,
  statistical method, and whether real execution is requested.

## Reference Map

- `references/lammps_parameters.md`: compact index and legacy entry point.
- `references/lammps_official_sources.md`: official documentation entry points for commands, packages, acceleration, ML pair styles, and errors.
- `references/lammps_input_validation.md`: static inspection contract for input/data/log/dump evidence.
- `references/lammps_force_fields_and_mlp.md`: classical, reactive, KIM, and MLP deployment evidence plus the `simflow-mlp` boundary.
- `references/lammps_md_workflows.md`: minimize, equilibration, production, transport, rerun, restart, smoke, and production workflows.
- `references/lammps_output_intake.md`: LAMMPS log/dump/data/restart intake, `lammps_output_intake_manifest`, and analysis handoff.
- `references/lammps_troubleshooting.md`: missing packages, lost atoms, dangerous builds, GPU/MPI, drift, and MLP runtime issues.
- `references/lammps_tools.md`: LAMMPS-specific tools (LAMMPS Python interface, bundled tools, Pizza.py) with command patterns and provenance. For general tools (MDAnalysis, OVITO, pymatgen), see `simflow-analysis-visualization/references/tooling_index.md`.

## Output artifacts

- Optional input manifest, force-field provenance note, MLP deployment manifest,
  validation report, LAMMPS output intake manifest, or handoff note.
- Record a helper-run manifest when using any helper, script, or external tool.
- Artifact metadata should record source data, command/tool, parameters,
  environment, outputs, and lineage.
- For input/log/dump inspection, prefer an inspection report covering missing
  inputs, force-field provenance, commands detected, risk warnings, local
  example motifs, and recommended artifacts.

## Status write rules

- Pass `project_root` explicitly before writing `.simflow/`.
- LAMMPS task labels are recipe/tag/helper metadata only; they do not determine
  the top-level workflow stage.
- Default to dry-run or static inspection only. Real local, remote, or HPC
  execution must pass the SimFlow approval gate.
- MLP-MD is a recipe/tag, not a new top-level stage. Production-readiness claims
  must pass MLP/readiness evidence checks.
- Keep missing inputs, incomplete provenance, parser limits, dry-run-only state,
  and blocked scientific claims visible in artifacts and handoff records.

## Checkpoint rules

- Do not create checkpoints for untracked conceptual guidance or file-format
  explanations.
- When LAMMPS evidence closes a tracked modeling, computation, or
  analysis_visualization boundary, associate the checkpoint with the workflow,
  canonical stage, and registered artifacts.
- Preserve failure evidence and a failure checkpoint when a tracked LAMMPS
  validation, execution, parsing, or handoff boundary fails.

## Optional Helper Scripts

- `scripts/inspect_lammps_inputs.py`: statically inspects input/data/log files
  and optional `lmp -h` output without running LAMMPS; produces input
  inspection and MLP deployment evidence.
- `scripts/generate_lammps_inputs.py`: narrow template helper for initial
  `minimize`, `nve`, `nvt`, and `npt` drafts; returns `needs_inputs` when
  `mlp_md` lacks model/type/package evidence.
- `scripts/parse_lammps_outputs.py`: output INTAKE adapter. Parses `log.lammps`
  thermo via the shared `LAMMPSParser` and scans dump/data headers for columns,
  units style, atom ids, image flags, frame count, box bounds, and masses, then
  emits a `lammps_output_intake_manifest` and handoff artifact. It does NOT
  compute RDF, MSD, diffusion, or any property claim; those belong to
  `simflow-analysis-visualization` (e.g. its `analyze_md_trajectory.py` helper).

These helper scripts are optional routes, not the only valid path. Official LAMMPS
examples, user-written scripts, Python, OVITO, Pizza.py, notebooks, or shell
commands are acceptable when evidence, lineage, and risks are recorded.

Per the SimFlow domain-skill script boundary (see `skills/README.md`), this
skill ships only `inspect_*` / `generate_*_inputs` / `parse_*_outputs` helpers.
Analysis and plotting helpers such as `analyze_*` or `plot_*` live under
`simflow-analysis-visualization`, not here.

## Prohibited actions

- Do not treat built-in LAMMPS helpers as the only valid parser, builder, or
  analysis path.
- Do not default unknown LAMMPS tasks to fixed MD aliases.
- Do not turn successful MLP model loading in LAMMPS into claims that training
  is validated, extrapolation is safe, or the model is production-ready.
- Do not turn LAMMPS output intake into final RDF/MSD/VACF, transport, elastic,
  or other property claims; those belong to `simflow-analysis-visualization`.
- Do not hide incomplete force-field provenance, energy drift, unequilibrated
  trajectories, missing timestep evidence, or missing statistical uncertainty.
- Do not store credentials, leak proprietary force-field/model files, or record
  private paths unnecessarily.
- Do not submit real local, remote, or HPC jobs without approval gate passage.

## Manual confirmation scenarios

- Force-field choice, mixing rules, charges, type mapping, timestep, ensemble,
  constraints, equilibration criteria, or statistical method is unclear.
- The request involves real execution, remote systems, proprietary force-field
  or model files, credentials, or high-cost resources.
- The analysis method would materially change the scientific conclusion.
