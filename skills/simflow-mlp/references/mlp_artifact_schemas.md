# Helper Evidence Schemas

Use these lightweight contracts for helper-produced JSON. They are guidance for
consistent evidence, not a global hard schema gate. The machine-readable soft
schema lives at `schemas/helper_evidence.schema.json`.

## Common helper evidence v1

Helper-produced evidence should use `schema_version:
simflow.helper_evidence.v1` when a helper is updated or newly added.

## Common fields

- `helper`: helper script or skill-specific helper name.
- `capability`: helper capability such as `static_input_inspection`,
  `manifest_generation`, `selected_output_parsing`, `model_metrics_summary`,
  or `production_readiness_review`.
- `status`: one of `success`, `warning`, `blocked`, `incomplete`,
  `skipped_optional_dependency`, or `capability_warning`.
- `stage`: canonical SimFlow stage where this evidence belongs.
- `activity`: stage-local activity such as `analysis`, `visualization`,
  `dataset_build`, or `validation_md`.
- `evidence_role`: concise role such as `dataset_manifest`, `model_metrics_summary`, `model_validation_report`, `training_run_manifest`, `anomaly_report`, or `mlp_handoff`.
- `source_files`: source file metadata records with path, presence, size, and
  hash when available.
- `actual_tool_used`: software, support level, command, version, and environment
  facts when known.
- `parser_status`: one of `parsed`, `partial`, `unrecognized`, `missing`,
  `malformed`, or `not_applicable`.
- `claim_limits`: explicit statements about what claims this evidence does not
  support.
- `recipe`: usually `mlp_md` when the evidence belongs to an MLP-MD workflow.
- `iteration_id`: active-learning round id when applicable.
- `toolchain`: user-provided toolchain list when known.
- `warnings`: list of `{code, message}` objects for degraded evidence.
- `limitations`: plain statements about what the helper did not prove.
- `parent_artifacts`: artifact ids that this evidence depends on.

## Status semantics

- `success`: requested evidence was read or summarized without degraded inputs.
- `warning`: at least one input is missing, malformed, partially parsed, or semantically incomplete, but useful evidence remains.
- `blocked`: the helper cannot complete the requested evidence task because required inputs are absent or unreadable.
- `incomplete`: evidence was created but is known to be unfinished or missing
  optional context.
- `skipped_optional_dependency`: the helper was skipped because an optional
  package or tool is unavailable.
- `capability_warning`: the requested action is outside helper support, such as real execution, input generation, or submit.

Helper evidence `status` is not the same thing as `simflow.result.v1`
`outcome`, stage status, readiness status, verification status, gate status,
or checkpoint status. Top-level statuses are compatibility fields when a
surface also returns nested `simflow_result` data.

Default helper report paths live under project-root `reports/<engine>/`.
Direct helpers do not register arbitrary report artifacts. Stage runners may
ingest/register outputs when those outputs become canonical stage artifacts.

## Production readiness

Scientific production-readiness evidence should include dataset lineage, training evidence, validation evidence, smoke-MD evidence, and anomaly criteria. Approval/gate evidence is a separate policy requirement and should only be required by helper scripts when the caller explicitly asks for approval readiness.

For MLP readiness helper output:

- `scientific_readiness.status` records whether the scientific evidence is
  ready or blocked.
- `scientific_readiness.semantic_issues` lists role-level minimum-field or
  status problems that block readiness.
- `production_md_gate_approved` records whether the optional
  `production_md_readiness` approval evidence was supplied and accepted.
- `real_submit_gate` should point to `hpc_submit` and state that a separate
  submit gate is required before real local, remote, or HPC execution.
- `real_submit_allowed` is a compatibility field in MLP readiness evidence and
  must remain `false`; production-readiness approval does not authorize submit.

`prepare_mlp_handoff` output should also use `simflow.helper_evidence.v1` so
handoff artifacts can be queried by evidence role, helper status, parser status,
recipe, and claim limits.
