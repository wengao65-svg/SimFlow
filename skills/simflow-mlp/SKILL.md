---
name: simflow-mlp
description: Provide engine-independent machine-learning-potential guidance for datasets, labels, training evidence, validation, active learning, and production readiness.
---

# Machine-Learning Potential Domain Skill

## Purpose

Act as the cross-tool MLP Domain Skill for the current Research Task Skill.
It does not own workflow progression or runtime state. Provider files and
commands remain owned by their engine-specific Domain Skill.

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

- `references/mlp_scope_and_toolchains.md`
- `references/mlp_dataset_and_labeling.md`
- `references/mlp_dft_labeling_consistency.md`
- `references/mlp_training_validation.md`
- `references/mlp_active_learning_readiness.md`
- `references/mlp_evidence_handoff.md`
- `references/mlp_artifact_schemas.md`
- `references/mlp_task_checklists.md`
- `references/mlp_troubleshooting.md`
