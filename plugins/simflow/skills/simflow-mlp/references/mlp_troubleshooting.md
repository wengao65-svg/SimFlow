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

## Label-protocol inconsistency symptoms

When MLP training labels come from DFT engines, additionally watch for (see `mlp_dft_labeling_consistency.md`):

- Protocol fingerprint mismatch across jobs in the same dataset — indicates mixed scientific settings (e.g., mixed cutoff energies, different SCF thresholds, or different smearing) that corrupt the PES.
- A single global pseudopotential/basis-set configuration applied to structures with multiple element combinations — breaks structure-to-pseudopotential matching.
- Active-learning rounds using a different scientific input fingerprint than the baseline — propagates protocol drift into the trained model.
- Trial, convergence-test, or benchmark jobs with stricter settings mixed into the production training set — silently introduces a second PES.
- Runtime metadata (parallelism, host, queue, executable path) written into the scientific input and entering the protocol fingerprint — causes false mismatches across machines.
