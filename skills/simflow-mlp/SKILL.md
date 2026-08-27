---
name: simflow-mlp
description: Provide engine-independent guidance for machine-learning interatomic potentials (MLPs/MLIPs), including dataset and DFT-label provenance, splits and leakage, training and fine-tuning evidence, validation metrics, uncertainty and extrapolation, transferability, active learning, deployment, and production MLP-MD readiness. Use when requests mention machine-learning, neural-network, foundation, or universal interatomic potentials; energy/force/stress labels; model validation; long MLP-MD; or frameworks such as NEP, DeePMD, MACE, NequIP, or Allegro. Combine with engine-specific Domain Skills for provider files and commands.
---

# Machine-Learning Potential Domain Skill

## Purpose

Provide cross-tool MLP methodology to any current Research Task Skills that
need it. It does not own workflow progression or runtime state. Provider files
and commands remain owned by relevant engine-specific Domain Skills, which may
be loaded alongside this Skill.

## Use when

- Designing or reviewing MLP datasets, labeling, splits, training evidence,
  validation, active learning, uncertainty, or production deployment.
- Comparing NEP, MACE, DeePMD, NequIP, Allegro, or custom potential evidence.
- Deciding whether an MLP is ready for a target scientific use.

## Do not use when

- The task only concerns one provider's input syntax or output file format.
- The task is general analysis with no MLP-specific methodological question.

## Domain principles

- Preserve dataset and label provenance from source structures through every
  transformation.
- Keep training, validation, transferability, stability, and production
  readiness as separate claims.
- Follow provider-defined training and restart semantics rather than imposing a
  universal schedule.
- Validate on configurations and observables relevant to the intended use.
- Treat active learning as a bounded evidence loop, not an automatic guarantee
  of coverage.
- Do not infer model quality from training loss alone.

## Minimum checks

- Dataset composition, frame counts, element coverage, units, labels, and DFT
  protocol consistency are known.
- Train/validation/test separation avoids leakage and duplicated structures.
- Energy, force, stress, and property metrics match the intended application.
- Outliers, extrapolation, physical failures, and long-run stability are tested.
- Active-learning acquisition, stopping conditions, and rejected configurations
  are explicit when used.
- Production deployment has model provenance, type mapping, software/version,
  and target-condition evidence.

## Common failure modes

- Mixing labels from inconsistent DFT settings without analysis.
- Reporting aggregate RMSE while hiding element, phase, or regime failures.
- Treating a random split as a transferability test.
- Calling a model production-ready after only short smoke runs.
- Confusing provider checkpoints, restarts, fine-tuning, and foundation-model
  adaptation.

## Escalate uncertainty when

- Label consistency, dataset ownership, target domain, or acceptance thresholds
  are unclear.
- Real training, large-scale labeling, remote execution, or destructive model
  replacement is requested.
- Available validation cannot support the intended production claim.

## Completion criteria

- Dataset, training, validation, and deployment claims are separated.
- Evidence gaps and target-domain limits are explicit.
- Readiness language matches the strongest completed validation, not intent.

## Optional references

Select references according to the evidence question: scope, dataset and
labels, training and validation, active learning and readiness, evidence
exchange, helper schemas, or troubleshooting. Combine with an engine-specific
Domain Skill when provider files or commands matter.

- `references/mlp_scope_and_toolchains.md`: Read when the trainer, labeling
  engine, MD provider, toolchain roles, or boundary between generic MLP
  methodology and provider-specific semantics is unclear.
- `references/mlp_dataset_and_labeling.md`: Read when designing or auditing
  dataset scope, configuration coverage, label provenance, units, exclusions,
  splits, leakage, or dataset lineage.
- `references/mlp_dft_labeling_consistency.md`: Read whenever an MLP dataset
  contains DFT energy, force, virial, or stress labels, especially for protocol
  fingerprints, pseudopotential/basis consistency, atom-order mappings, or
  active-learning label inheritance.
- `references/mlp_training_validation.md`: Read when reviewing training mode,
  fine-tuning, restart, optimizer/loss/scheduler evidence, metrics, property
  validation, transferability, stability, or smoke MD.
- `references/mlp_active_learning_readiness.md`: Read when designing or
  reviewing active-learning rounds, acquisition and anomaly criteria, stopping
  conditions, residual risk, or production MLP-MD readiness.
- `references/mlp_evidence_handoff.md`: Read when preparing a concise evidence
  package that must communicate datasets, labels, training, models, validation,
  readiness gaps, and next actions.
- `references/mlp_artifact_schemas.md`: Read only when creating, validating, or
  interpreting helper-produced JSON using `simflow.helper_evidence.v1`; it is
  not required for ordinary scientific review.
- `references/mlp_task_checklists.md`: Read when a compact dataset,
  DFT-label-protocol, validation, or readiness audit checklist is useful.
- `references/mlp_troubleshooting.md`: Read when evidence is missing,
  conflicting, malformed, semantically incomplete, protocol-inconsistent, or
  being used to support a stronger claim than it permits.
