# MLP Active Learning And Readiness

Active-learning evidence should record:

- Iteration id, candidate pool, selection/acquisition method, selected structures, label results, failed labels, dataset update, retraining, and validation changes.
- Uncertainty or anomaly criteria, including thresholds and what action each threshold triggers.
- Stop condition and residual risk.

Production MLP-MD readiness requires dataset/labeling, training, validation,
smoke MD, anomaly criteria, active-learning round review, and explicit approval
evidence.

Minimum production-readiness evidence must include:

- Dataset manifest with complete lineage.
- Labeling manifest with completed/passing status and label provenance.
- Training-run manifest with completed/passing status and model artifact identity.
- Metrics summary with metric values or metric-file summaries.
- Validation report with passing status and validation-domain or property context.
- Smoke-MD manifest with passing status and steps, duration, trajectory, or run manifest.
- Anomaly report with defined thresholds.
- Active-learning round manifest with completed/passing status and iteration,
  candidate/selection, dataset-update, or validation-change context.

The production-readiness approval gate records a scientific readiness decision
only. It must not set `real_submit_allowed: true`; real local, remote, or HPC
execution still requires the independent submit gate.
