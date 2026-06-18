# MLP Troubleshooting

Common evidence gaps:

- Dataset files exist but label provenance is missing.
- Training metrics lack units, split names, or test-domain separation.
- Force metrics look acceptable but property-level validation is absent.
- Active-learning rounds lack candidate-pool or selection records.
- Long MLP-MD claims lack smoke tests, anomaly thresholds, or approval.
- Production-readiness inputs are placeholder or empty JSON files.
- Evidence role paths point to directories or non-file paths instead of JSON evidence files.
- A helper output has `warning`, `blocked`, `incomplete`, `capability_warning`, or a blocking parser status but is being cited as ready evidence.

Report the blocked claim and the minimum evidence needed to revisit it.
