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
production-length MLP-MD. A readiness pass records a scientific readiness
decision; it is not a submit permission, does not trigger execution, and does
not run local, remote, or HPC jobs. MLP readiness helper evidence uses
`production_md_gate_approved` for this readiness decision; `real_submit_allowed`
must remain false until independent `hpc_submit` evidence and a job record
exist.

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

`vasp`, `cp2k`, `lammps`, `gpumd`, and `nep` currently have tool-level SimFlow
helper support. `simflow-gpumd` supports bounded input preparation, static
validation, dry-run planning, selected output parsing, manifest generation, and
evidence handoff. It does not expose GPUMD/NEP real execution or submit as
helper-supported actions. Other MLP-MD tools such as `neptrainkit`,
`deepmd`, `mace`, `nequip`, `allegro`, `ase`, and `python` are classified by
the shared toolchain contract, not by this recipe file.

When a user asks a helper to automate a `tracked_only` or `unknown` tool, it
returns a `capability_warning` rather than pretending to support the engine.
The host agent can still use user scripts, official documentation, outputs,
checks, and approvals, and may append one logical record when durable
provenance is useful.

Use the same generic computation evidence intake for DeePMD, MACE, NequIP,
Allegro, GROMACS, QE, custom Python, or any other tracked-only tool.
The intake is not an executor. It summarizes user-provided calculation
manifests, inputs, validation, dry-run evidence, resources, commands, versions,
environment, and provenance. A real submit is recorded as one compact run event
only after immutable-plan approval and actual submission; scientific readiness
alone never grants submit permission or requires a checkpoint.
