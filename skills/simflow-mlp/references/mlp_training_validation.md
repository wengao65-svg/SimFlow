# MLP Training And Validation

Training evidence should record:

- Model family, descriptor or architecture, loss terms, weights, optimizer/schedule when known, seed, training hardware when relevant, and model artifact hashes.
- Energy, force, and stress metrics with units and split names.
- Property-level validation relevant to the target use case, not only aggregate force error.
- Short validation MD or smoke tests before any long production MLP-MD.

Metrics summaries should not declare pass/fail unless thresholds and target-domain context are explicit.

For production-readiness review, minimum semantic evidence is stricter than file
presence:

- Training evidence must have a passing/completed status and identify model artifacts.
- Metrics evidence must contain metric values, metric file summaries, or threshold comparisons.
- Validation evidence must have a passing status and record validation domain, property validation, or metric context.
- Evidence with `blocked`, `incomplete`, `capability_warning`, `warning`, or missing/malformed/unrecognized parser status must not be promoted to production-ready scientific readiness.
