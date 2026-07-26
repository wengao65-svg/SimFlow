# MLP Task Checklists

## Dataset audit

- Identify dataset files and parent artifacts.
- Record structure counts when safely available.
- Check split definitions and label provenance.

## DFT label-protocol audit

For DFT-labeled MLP training datasets, additionally check (engine-agnostic; see `mlp_dft_labeling_consistency.md`):

- One explicit label protocol is defined for the dataset, with a recorded fingerprint (SHA256 of the normalized scientific input after stripping runtime metadata).
- All jobs in the dataset share the same protocol fingerprint; mismatches are flagged as violations.
- Each structure's pseudopotential/basis-set assignment matches its element order; the same element's variant is consistent across all element combinations.
- Element-order normalization, when applied, has a saved `structure_to_source_atom_index` map that is a complete `0..N-1` permutation.
- Runtime metadata (parallelism/host/queue/executable path) is separated from the scientific protocol and does not enter the protocol fingerprint.
- Trial, convergence-test, performance-benchmark, or alternative-protocol jobs are isolated from the production dataset.
- For active-learning datasets, all rounds inherit the same frozen protocol fingerprint.

## Validation review

- Record metric names, units, split names, and thresholds if provided.
- Separate interpolation metrics from domain-transfer metrics.
- Check property-level validation for the intended use.

## Readiness review

- Require complete dataset lineage, labeling provenance, training/model artifact identity, metrics, validation, smoke MD, anomaly thresholds, and approval evidence before production MLP-MD.
- Record missing evidence as blocked or degraded, not passed.
- Treat empty JSON, warning status, blocked/incomplete/capability-warning status, or missing/malformed/unrecognized parser status as readiness blockers.
- Treat directories or other non-file paths as missing evidence; `role=path`
  entries must point to regular JSON evidence files.
