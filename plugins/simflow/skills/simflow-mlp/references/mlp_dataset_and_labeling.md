# MLP Dataset And Labeling

Dataset evidence should record:

- Scientific target and target configuration domain, including the phases,
  compositions, temperatures, pressures, defects, interfaces, reactions, or
  properties the model is expected to cover.
- Source structures, configuration domains, element coverage, counts, and selection criteria.
- Reference-label source, DFT settings or other label provenance, failed-label exclusions, and convergence limits.
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
