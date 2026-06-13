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
| Sampling, DFT labeling, MLP training, validation MD, long MD | `computation` |
| Candidate selection, dataset audit, metrics, anomaly detection, active-learning decision | `analysis_visualization` |
| Methods, results, evidence map, handoff | `writing` |

Active learning is represented as a loop between `computation` and
`analysis_visualization`, with `production_md_readiness` controlling entry to
production-length MLP-MD.

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

Only `vasp`, `cp2k`, and `lammps` currently have SimFlow helper support. Other
MLP tools such as `gpumd`, `nep`, `neptrainkit`, `deepmd`, `mace`, `nequip`,
and `allegro` are tracked for provenance and handoff unless a dedicated helper
is added later.
