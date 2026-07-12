# MLP-MD Analysis Readiness

Use this reference when MD outputs come from a machine-learning potential and
the analysis may support model, trajectory, or production-readiness claims.

## Required Evidence

- model identity, deployment manifest, training/validation handoff, active-learning round, and force-field/MLP provenance.
- smoke-run status, trajectory length, anomaly checks, extrapolation or uncertainty indicators, and failed-frame handling.
- intended claim: deployment works, qualitative trend, property estimate, production MLP-MD readiness, or real production execution.

## Methods

- Link trajectory analysis to MLP evidence roles from `simflow-mlp`, including dataset, labeling, training, metrics, validation, smoke MD, anomaly thresholds, and readiness gate where relevant.
- Keep property analysis separate from model-readiness analysis: diffusion, RDF, or transport results still need their own method references.
- Record out-of-domain structures, warning indicators, unstable frames, and comparisons to DFT/experiment/literature when available.

## Claim Limits

LAMMPS/GPUMD/ASE can show that an MLP ran, but production MLP-MD readiness
requires validation and gate evidence. Do not infer transferability or
production safety from a successful trajectory alone.
