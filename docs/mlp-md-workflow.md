# MLP-MD Workflow Recipe

`mlp_md` is a SimFlow recipe/tag for machine-learning-potential-driven
molecular dynamics. It does not add top-level workflow stages and it does not
make SimFlow a training or MD executor.

The canonical stage mapping remains:

| MLP-MD activity | SimFlow stage |
| --- | --- |
| Literature review, method selection, reference-label standards | `literature_review` |
| Experimental design, sampling plan, labeling standard, validation criteria | `proposal` |
| System definition, initial structures, solvation, transformations | `modeling` |
| Sampling, DFT labeling, MLP training, validation MD, smoke MD | `computation` |
| Candidate selection, dataset audit, metrics, anomaly detection, active-learning decision | `analysis_visualization` |
| Methods, results, evidence map, handoff | `writing` |

Active learning is represented as a loop between `computation` and
`analysis_visualization`, with `production_md_readiness` controlling entry to
production-length MLP-MD. A readiness pass records permission to proceed; it is
not itself a submit action and does not run local, remote, or HPC jobs. MLP
readiness helper evidence uses `production_md_gate_approved` for this decision;
`real_submit_allowed` must remain false until independent `hpc_submit` evidence
and a job record exist.

Recommended artifact metadata:

```json
{
  "recipe": "mlp_md",
  "iteration_id": "round_000",
  "evidence_role": "dataset_manifest",
  "toolchain": ["cp2k", "vasp", "gpumd", "nep", "neptrainkit"],
  "parent_artifacts": ["art_previous_step"]
}
```

## Toolchain Semantics

MLP-MD uses the same shared toolchain contract as DFT, AIMD, classical MD,
phonon, and NEB recipes. Proposals may name a primary `software` value and a
multi-tool `toolchain`, but those fields are not workflow admission
requirements. They are planning and provenance metadata from the proposal
stage.

Proposal contracts expose:

- `toolchain_plan`: activity-level tool suggestions such as sampling,
  labeling, training, validation MD, and analysis. These activity labels come
  from recipe metadata and are not an executor DAG.
- `helper_support`: support levels for named tools. Current values are
  `helper_supported`, `tracked_only`, and `unknown`.
- `actual_tool_used`: artifact/runtime metadata for the concrete tool, command,
  version, and environment when known.

Only `vasp`, `cp2k`, and `lammps` currently have tool-level SimFlow helper
support. GPUMD and NEP remain `tracked_only` at the tool level, but
`simflow-gpumd` exposes limited capability-level helpers for static input
inspection, manifest generation, selected output parsing, and evidence handoff.
It does not expose GPUMD/NEP input generation, real execution, or submit as
helper-supported capabilities. Other MLP-MD tools such as `neptrainkit`,
`deepmd`, `mace`, `nequip`, `allegro`, `ase`, and `python` are classified by
the shared toolchain contract, not by this recipe file.

When a user asks a built-in stage runner to automate a `tracked_only` or
`unknown` tool, the stage returns a `capability_warning` and keeps the stage in
`waiting` status. The workflow can still record user scripts, official-docs
usage, outputs, checks, and approvals as artifacts.

Use the same generic computation evidence intake for GPUMD, NEP, DeePMD, MACE,
NequIP, Allegro, GROMACS, QE, custom Python, or any other tracked-only tool.
The intake is not an executor; it records user-provided calculation manifests,
input files, validation reports, dry-run reports, resource estimates, commands,
versions, environment, and lineage. When readiness is satisfied, the waiting
`computation` stage can be explicitly completed and checkpointed. A
`job_record_if_submitted` artifact is required only after a real submit is
recorded.
