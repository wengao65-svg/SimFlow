# Skills Directory

SimFlow is skill-first, but not every bundled skill has the same role. The
canonical workflow-layer skills define the current research-stage contract:

- `simflow`
- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`
- `simflow-safety-gates`

These skills describe SimFlow's current workflow-layer semantics: research
intent, evidence boundaries, artifact tracking, checkpoints, lineage, safety
gates, and handoff discipline. They do not make SimFlow a centralized workflow
executor.

Other `simflow-*` skills are optional domain assistants or focused workflow
helpers. Legacy executor skill entries such as `simflow-pipeline`,
`simflow-stage`, `simflow-compute`, and older stage aliases are no longer
discoverable as skills. Project intake, stage execution, and pipeline behavior
has migrated into `runtime/simflow_helpers`, so new tests and integrations
should import those helpers directly rather than adding wrapper scripts back
under legacy skill directories.

Engine skills such as `simflow-vasp`, `simflow-cp2k`, `simflow-lammps`, and
`simflow-gpumd` are the supported optional domain assistants in the current
product build. `simflow-mlp` is also a Domain Assistant, but its scope is
cross-tool MLP lifecycle and readiness methodology rather than one engine. It
can inspect existing evidence, build manifests, parse narrow output subsets,
and prepare handoff records, but it does not run training or MD. `simflow-qe` and
`simflow-gaussian` are reserved unsupported
placeholders; they should only record user-provided files as generic artifacts
when traceability is requested.

Domain Assistant is a product role. Tool-level and capability-level helper
support come from `workflow/toolchains/capabilities.json`. Optional scripts may
emit `simflow.helper_evidence.v1` records, but that helper-evidence envelope is
an output contract, not a Skill category.

When adding new skills, keep hard requirements limited to safety and
traceability. Prefer guidance, recommended evidence, and handoff notes over
fixed parser, builder, software, or report-file requirements.
