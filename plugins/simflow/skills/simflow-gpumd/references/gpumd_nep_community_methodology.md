# GPUMD/NEP Community Methodology

Source:
Untracked local community material under
`.simflow/community-gpumd-nep/`

Status:
Community-derived, cleaned and checked against current official documentation
where possible. The audit used the GPUMD/NEP v5.5 documentation available on
2026-07-10.

Not authoritative:
The original material and generated summaries are not official GPUMD or NEP
documentation. This reference omits raw conversations, identities, contact
details, private cases, duplicated parameter documentation, and unsupported
fixed recommendations.

General dataset, labeling, validation, active-learning, and production-MD
methodology belongs to `simflow-mlp`. This document retains only
provider-specific or version-sensitive GPUMD/NEP guidance.

## Stable methodology

### NEP training-mode separation

Methodology:
Record from-scratch training, ordinary checkpoint/restart, foundation-model
fine-tuning, and optional community training strategies as distinct modes.

Applicability:
All NEP training evidence and handoffs.

Non-applicability:
Do not infer equivalent modes for another trainer without its provider
documentation.

Evidence status:
The separation between official fine-tuning and ordinary restart is
officially-supported; the broader evidence distinction is audit methodology.

Official-document consistency:
Consistent with the v5.5 `fine_tune` and `nep.restart` documentation.

Source-code consistency:
Not independently checked in this audit because direct repository access was
unavailable.

Version sensitivity:
The evidence distinction is stable; exact keywords and compatible files are
version-sensitive implementation details.

Community confidence:
High for the need to distinguish modes.

Residual risk:
Community material sometimes conflates foundation fine-tuning with ordinary
restart or a later loss-policy change.

Recommended use:
Require an explicit training mode and parent-file lineage in every NEP
training manifest.

### Minority-species evidence

Methodology:
Inspect per-species coverage and errors when a small number of atoms or
structures represent a scientifically important species. A provider-specific
weight may be considered, but no fixed multiplier is prescribed.

Applicability:
Compositionally imbalanced NEP datasets.

Non-applicability:
Datasets where all relevant species and environments are already adequately
represented.

Evidence status:
Community-derived methodology supported by the official existence of
type-specific weighting controls.

Official-document consistency:
Consistent with provider controls; fixed community values were removed.

Source-code consistency:
Not independently checked.

Version sensitivity:
Parameter syntax is version-sensitive; the coverage audit is stable.

Community confidence:
Medium.

Residual risk:
Reweighting can hide missing configurations rather than repair coverage.

Recommended use:
Audit coverage first, then record any weighting choice and remaining risk.

### Noisy virial-label decision

Methodology:
Treat virial inclusion, exclusion, or down-weighting as a documented modeling
decision. If virial labels are reduced or omitted, validate pressure, density,
volume response, and target NPT behavior independently.

Applicability:
NEP datasets with demonstrably noisy or ill-defined virial labels.

Non-applicability:
Do not disable virial evidence by default for all liquids, molecular systems,
vacuum cells, or low-dimensional materials.

Evidence status:
Community-derived and scientifically plausible, with conflicting community
reports about pressure and density consequences.

Official-document consistency:
The provider supports virial loss weighting but does not prescribe a universal
zero-weight policy.

Source-code consistency:
Not independently checked.

Version sensitivity:
The loss keyword is version-sensitive; the validation requirement is stable.

Community confidence:
Medium for the tradeoff, low for blanket recommendations.

Residual risk:
Good force metrics can coexist with poor pressure or density predictions.

Recommended use:
Record the label-quality evidence, chosen loss policy, target NPT tests, and
residual risk.

### Short-range prior decision

Methodology:
Decide whether an analytic short-range prior is needed from the target domain,
minimum separations, collision processes, and available labels. Do not use it
as a substitute for dataset and label auditing.

Applicability:
NEP models expected to encounter close approaches, high temperature,
irradiation, deposition, or collision events.

Non-applicability:
Do not declare the feature mandatory for every liquid or every NEP model.

Evidence status:
The feature is official; the decision framework is cleaned community
methodology.

Official-document consistency:
Consistent after removing fixed cutoff recommendations and mandatory wording.

Source-code consistency:
Not independently checked.

Version sensitivity:
Exact keyword syntax is version-sensitive; documenting the modeling decision
is stable.

Community confidence:
Medium.

Residual risk:
An inappropriate prior or transition range can distort the target region.

Recommended use:
Record why the prior is included or omitted and validate both normal and
close-contact configurations.

### GPUMD failure triage

Methodology:
Treat illegal-memory-access or out-of-memory failures as multi-cause symptoms.
Inspect the initial structure, recent trajectory, integration settings,
neighbor growth, model domain, device memory, and complete error context.

Applicability:
GPUMD runtime crashes and abrupt structural failures.

Non-applicability:
Do not assign a fixed probability or assume the potential is always the cause.

Evidence status:
Community-derived troubleshooting case.

Official-document consistency:
No conflict when presented as bounded triage rather than a diagnostic fact.

Source-code consistency:
Not independently checked for individual CUDA error paths.

Version sensitivity:
Error text and diagnostic outputs are version-sensitive.

Community confidence:
Medium.

Residual risk:
The same device error can result from unrelated input, model, integration, or
hardware conditions.

Recommended use:
Collect reproducible inputs and diagnostics before changing model or runtime
parameters.

## Version-sensitive notes

### Foundation-model fine-tuning

Methodology:
GPUMD/NEP v5.5 supports foundation-model fine-tuning through
`fine_tune <nep_model_file> <nep_restart_file>` and documents a NEP89 example.

Applicability:
Version-matched NEP foundation models with compatible model and restart files.

Non-applicability:
Ordinary continuation of the same training run.

Evidence status:
officially-supported.

Official-document consistency:
Confirmed in the v5.5 `fine_tune` parameter page.

Source-code consistency:
Not independently checked in this audit.

Version sensitivity:
version-sensitive implementation.

Community confidence:
High because the functionality is official, not merely a community claim.

Residual risk:
Model architecture, element ordering, energy reference, or restart
incompatibility can invalidate the fine-tuning lineage.

Recommended use:
Record the exact version, both parent files and hashes, compatibility evidence,
target dataset, and resulting model.

### NEP optional two-step training

Methodology:
After an ordinary training run, some community workflows continue from a
checkpoint while changing selected loss, batching, or regularization policy.
No fixed values are retained here.

Applicability:
Only NEP tasks where the first-run evidence and target metrics justify a
provider-specific continuation experiment.

Non-applicability:
MACE, DeePMD, NequIP, Allegro, or any trainer without independently documented
equivalent behavior. It is not required for every NEP model.

Evidence status:
community-derived; NEP-specific; optional.

Official-document consistency:
Official documentation supports restart and configurable loss parameters but
does not prescribe this community two-step training strategy.

Source-code consistency:
Not independently checked for the community policy.

Version sensitivity:
version-sensitive implementation.

Community confidence:
Medium for usefulness in selected cases; low for universal parameter advice.

Residual risk:
Changing multiple controls at once obscures causality and can degrade force,
virial, or transferability evidence.

Recommended use:
Treat it as an optional experiment with before/after metrics, checkpoint
lineage, stopping conditions, and rollback criteria.

### Energy-reference handling

Methodology:
Check energy-reference consistency before NEP training or foundation-model
fine-tuning, especially for mixed label providers or large absolute energies.
Do not prescribe one universal shift operation or threshold.

Applicability:
Cross-code datasets, merged datasets, and foundation-model fine-tuning.

Non-applicability:
Datasets with documented and already consistent reference conventions.

Evidence status:
Community-derived, partially supported by official fine-tuning and dataset
requirements.

Official-document consistency:
Consistent at the provenance level; fixed warning thresholds and scripts were
removed.

Source-code consistency:
Needs version-matched source confirmation for numerical implementation claims.

Version sensitivity:
version-sensitive implementation.

Community confidence:
Medium.

Residual risk:
An incorrect shift can hide a label mismatch or break comparability with a
foundation model.

Recommended use:
Record the original convention, transformation, per-element references when
used, and validation before and after transformation.

### Multi-GPU geometry and neighbor diagnostics

Methodology:
Treat domain-decomposition geometry errors and `neighbor.out`-style evidence as
version-sensitive diagnostics. Confirm the current producer, format, cutoff,
box dimensions, and GPU count before interpretation.

Applicability:
GPUMD multi-GPU runs or toolchains that produce neighbor diagnostics.

Non-applicability:
Single-GPU runs or versions that do not produce the named diagnostic file.

Evidence status:
Community-derived and requires version gating.

Official-document consistency:
No stable cross-version file-format claim is made.

Source-code consistency:
Needs version-matched source or official documentation confirmation.

Version sensitivity:
version-sensitive implementation.

Community confidence:
Low to medium.

Residual risk:
Fixed neighbor-count or box-length thresholds can be obsolete or task
dependent.

Recommended use:
Preserve the diagnostic as runtime/structural evidence with version and parser
limitations; do not encode a fixed threshold in SimFlow.

## Needs human review

The cleaned inventory leaves the following claims unresolved rather than
promoting them to guidance:

- Whether disabling a particular regularization term is generally beneficial
  for ordinary NEP restart.
- Whether full-batch optimization is broadly preferable in later NEP training.
- When virial labels should be omitted rather than repaired or re-labeled.
- Provider-version details for missing-value sentinels and neighbor
  diagnostics.
- Electrostatic or charge-model commands not confirmed in the current official
  documentation set.
