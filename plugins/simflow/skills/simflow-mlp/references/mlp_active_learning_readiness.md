# MLP Active Learning And Readiness

Active-learning evidence should record:

- Iteration id, candidate pool, selection/acquisition method, selected structures, label results, failed labels, dataset update, retraining, and validation changes.
- Uncertainty or anomaly criteria, including thresholds and what action each threshold triggers.
- Stop condition and residual risk.

Candidate selection should favor configurations that add target-domain
coverage and remain physically interpretable enough to label. Do not treat a
fully collapsed or malformed trajectory frame as useful solely because it is
extreme. Record whether short-range, long-range, charge, or other physical
priors were considered for poorly sampled regions.

Production MLP-MD readiness requires dataset/labeling, training, validation,
smoke MD, anomaly criteria, an active-learning decision manifest, and explicit
approval evidence. The manifest is required even when active learning was not
used; active learning itself is not mandatory for every reliable model.

Minimum production-readiness evidence must include:

- Dataset manifest with complete lineage.
- Labeling manifest with completed/passing status and label provenance.
- Training-run manifest with completed/passing status and model artifact identity.
- Metrics summary with metric values or metric-file summaries.
- Validation report with passing status and validation-domain or property context.
- Smoke-MD manifest with passing status and steps, duration, trajectory, or run manifest.
- Anomaly report with defined thresholds.
- Active-learning round manifest with completed/passing status. When active
  learning was used, record iteration, candidate/selection, dataset-update, or
  validation-change context. When it was not used, record
  `active_learning_used: false`, the decision rationale, and residual risk.
- Target-scale validation when production systems are materially larger or
  explore slower collective modes than the smoke-test systems.

The production-readiness approval gate records a scientific readiness decision
only. It must not set `real_submit_allowed: true`; real local, remote, or HPC
execution still requires the independent submit gate.
