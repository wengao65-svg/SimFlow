# MLP Dataset And Labeling

Dataset evidence should record:

- Scientific target and target configuration domain, including the phases,
  compositions, temperatures, pressures, defects, interfaces, reactions, or
  properties the model is expected to cover.
- Source structures, configuration domains, element coverage, counts, and selection criteria.
- Reference-label source, DFT settings or other label provenance, failed-label exclusions, and convergence limits. **For MLP training DFT labels, the reference-label source must additionally record: the label-protocol fingerprint (SHA256 of the normalized scientific input after stripping runtime metadata), pseudopotential/basis-set assignment, and the index map from element-order normalization.** Incomplete or unfrozen label-source evidence must be recorded as degraded and must not be claimed production-ready.
- Train/validation/test split definitions and whether splits are random, stratified, time-based, composition-based, or domain-held-out.
- Hashes or immutable identifiers for dataset files and parent artifacts.

Prefer configuration diversity and target-domain coverage over repeated nearby
frames. Keep reference-label theory level, numerical settings, units, and
energy reference conventions consistent or record explicit transformations.
Isolate unconverged, malformed, or clearly nonphysical labels; do not apply a
fixed outlier threshold without considering whether an extreme configuration
is part of the intended scientific domain.

Missing or ambiguous label provenance blocks strong model-quality claims.

For production-readiness review, a dataset manifest should additionally expose
`lineage_complete: true` only when all source dataset files are present, split
labels are recorded, and the reference label source is recorded. Missing files,
missing split definitions, or missing label source should remain degraded
evidence, not a production-ready dataset claim.

## Label-protocol consistency

For DFT labels used in MLP training (N structures sent to a DFT engine for single-point energy/forces/stress, then fed to a trainer such as GPUMD/NEP, DeePMD, or MACE), the dataset must satisfy the single-reference-protocol contract — all labels come from one frozen set of scientific settings, **regardless of which DFT engine is used**. Core clauses:

- One single-fidelity dataset corresponds to one explicit label protocol; the whole dataset shares one protocol fingerprint.
- Structure element order matches pseudopotential/basis-set assignment; the same element's variant is consistent across all element combinations; when reordering atoms, save the index map.
- Scientific settings (precision/physical parameters affecting the PES) are single across the dataset; runtime metadata (parallelism/host/queue/executable path) may vary per job and does not enter the protocol fingerprint.
- Production labels and trial/comparison/alternative-protocol jobs are recorded separately; only results passing the protocol check enter the dataset.
- Active-learning rounds inherit the current protocol; a protocol change establishes a new dataset/model lineage.
- Engine-specific execution details (tag values, pseudopotential generation commands, dry-run, parallelism strategy) are owned by the corresponding engine skill — VASP → `simflow-vasp`, CP2K → `simflow-cp2k`, other engines → consult official docs and record explicit provenance.

See `mlp_dft_labeling_consistency.md` for details.
