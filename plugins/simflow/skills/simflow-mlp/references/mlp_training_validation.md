# MLP Training And Validation

Training evidence should record:

- Model family, descriptor or architecture, loss terms, weights, optimizer/schedule when known, seed, training hardware when relevant, and model artifact hashes.
- Energy, force, and stress metrics with units and split names.
- Property-level validation relevant to the target use case, not only aggregate force error.
- Short validation MD or smoke tests before any long production MLP-MD.

Metrics summaries should not declare pass/fail unless thresholds and target-domain context are explicit.
