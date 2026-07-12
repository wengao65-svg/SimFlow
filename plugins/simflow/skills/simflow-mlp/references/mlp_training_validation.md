# MLP Training And Validation

## Provider-defined training policy

Each trainer may implement optimization, loss scheduling, learning-rate
scheduling, restart, fine-tuning, multi-task training, early stopping, or
explicit stage transitions differently. Record the actual provider policy;
this reference does not prescribe a provider-independent training-phase
sequence.

Training evidence should distinguish:

- From-scratch training from ordinary checkpoint restart.
- Foundation-model fine-tuning from restart of the same training lineage.
- Continuous loss-weight scheduling from a discrete provider-defined stage
  transition.
- Learning-rate scheduler behavior from loss policy.
- Trainer-internal changes from outer active-learning iterations.

Training evidence should record:

- Trainer and version, model family, descriptor or architecture, training mode,
  loss terms and policy, optimizer, scheduler, checkpoint lineage, stopping
  conditions, seed, training hardware when relevant, and model artifact hashes.
- Energy, force, and stress metrics with units and split names.
- Property-level validation relevant to the target use case, not only aggregate force error.
- Short validation MD or smoke tests before any long production MLP-MD.

Metrics summaries should not declare pass/fail unless thresholds and target-domain context are explicit.

Aggregate RMSE alone does not establish reliability. Validation should include
the intended thermodynamic conditions, configuration domains, system scales,
and target properties. A stable small-system smoke test does not by itself
establish large-system production readiness.

For production-readiness review, minimum semantic evidence is stricter than file
presence:

- Training evidence must have a passing/completed status and identify model artifacts.
- Metrics evidence must contain metric values, metric file summaries, or threshold comparisons.
- Validation evidence must have a passing status and record validation domain, property validation, or metric context.
- Evidence with `blocked`, `incomplete`, `capability_warning`, `warning`, or missing/malformed/unrecognized parser status must not be promoted to production-ready scientific readiness.
