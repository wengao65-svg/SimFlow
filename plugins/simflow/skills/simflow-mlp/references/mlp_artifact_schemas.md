# MLP Artifact Schemas

Use these lightweight contracts for helper-produced JSON. They are guidance for consistent evidence, not a global hard schema gate.

## Common fields

- `status`: one of `success`, `warning`, `blocked`, or `capability_warning`.
- `evidence_role`: concise role such as `dataset_manifest`, `model_metrics_summary`, `model_validation_report`, `training_run_manifest`, `anomaly_report`, or `mlp_handoff`.
- `recipe`: usually `mlp_md` when the evidence belongs to an MLP-MD workflow.
- `iteration_id`: active-learning round id when applicable.
- `toolchain`: user-provided toolchain list when known.
- `warnings`: list of `{code, message}` objects for degraded evidence.
- `limitations`: plain statements about what the helper did not prove.

## Status semantics

- `success`: requested evidence was read or summarized without degraded inputs.
- `warning`: at least one input is missing, malformed, partially parsed, or semantically incomplete, but useful evidence remains.
- `blocked`: the helper cannot complete the requested evidence task because required inputs are absent or unreadable.
- `capability_warning`: the requested action is outside helper support, such as real execution, input generation, or submit.

## Production readiness

Scientific production-readiness evidence should include dataset lineage, training evidence, validation evidence, smoke-MD evidence, and anomaly criteria. Approval/gate evidence is a separate policy requirement and should only be required by helper scripts when the caller explicitly asks for approval readiness.
