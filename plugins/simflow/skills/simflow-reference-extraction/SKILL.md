---
name: simflow-reference-extraction
description: Guide traceable recovery of numerical reference data from scientific source archives, tables, PDFs, vector figures, and raster figures without overstating reconstructed evidence.
---

# Scientific Reference Extraction

## Purpose

Help the agent recover numerical reference data from known scientific sources
while preserving source authority, calibration, uncertainty, and the distinction
between author-provided values and figure reconstruction.

## Use when

- The user wants numerical values from a known paper, supplement, source archive,
  table, PDF figure, or standalone scientific image.
- A simulation result needs a traceable literature reference dataset for later
  comparison.
- Existing figure digitization needs provenance, calibration, or visual
  validation.

## Do not use when

- The primary task is discovering or screening papers; use the literature-review
  Task Skill.
- The data are already available and the task is statistical comparison,
  interpretation, or plotting; use the analysis-visualization Task Skill.
- The user only needs citation formatting or manuscript prose.

## Task principles

- Prefer the strongest available source in this order:
  `A0 -> A1 -> A2 -> B1 -> B2 -> C1 -> C2`.
- Treat source selection as a scientific decision. A file discovered in an
  archive is not automatically the data behind the target figure.
- Keep exact source values separate from reconstructed or transformed values.
- Preserve source hashes, coordinates, calibration anchors, units, conditions,
  series mapping, uncertainty fields, and review status when applicable.
- Use semantic judgment for the target figure, panel, legend mapping, axes,
  units, and conditions. Use deterministic tools for archive safety, geometry,
  normalization, calibration, and validation.
- Do not silently smooth, interpolate, extrapolate, fill occluded regions,
  convert units, or invent unsupported significant digits.
- Helpers are optional and standalone. They do not initialize SimFlow state or
  record a run unless the caller explicitly requests runtime recording.

## Minimum checks

- The target paper, figure, panel, quantity, units, and conditions are identified.
- Structured author data and plotting source were checked before figure
  reconstruction was chosen.
- Axis and colorbar scales, tick anchors, series mapping, and error-bar meaning
  are explicit and visually checked.
- Figure-derived rows retain source coordinates and an honest provenance grade.
- Generated overlays, masks, or reconstructions align with the intended marks.
- Missing, occluded, ambiguous, or invalid values remain missing or flagged.

## Common failure modes

- Describing vector or raster reconstruction as author raw data.
- Digitizing a rendered page when an embedded image or source table exists.
- Mapping legend symbols, annotations, or frame lines as data.
- Assuming plot-frame bounds equal numerical axis limits without evidence.
- Ignoring logarithmic axes, colorbars, broken axes, or asymmetric uncertainty.
- Treating parser success or a visually plausible overlay as scientific
  verification.

## Escalate uncertainty when

- Multiple source files or panels plausibly represent the requested result.
- Marker groups, colors, paths, error bars, axes, or colorbar bounds cannot be
  mapped unambiguously.
- Resolution, compression, occlusion, non-Cartesian geometry, or complex table
  layout materially limits recoverable precision.
- A weaker reconstruction conflicts with structured source data.
- Replacing an existing output directory would destroy persistent evidence.

## Completion criteria

- The requested values are delivered in a traceable tabular form or the reason
  they cannot be recovered is explicit.
- Source authority and extraction method are represented by the correct
  provenance grade.
- Calibration, source coordinates, uncertainty, transformations, and review
  limitations are sufficient to audit the result.
- Validation artifacts support the extraction without being presented as proof
  of the underlying scientific claim.

## Optional references

Load only the material needed for the current source:

- `references/provenance.md`: source authority and A0-C2 grading.
- `references/source-extraction.md`: archives, raw files, plotting source, TeX
  tables, and verbatim numerical blocks.
- `references/vector-extraction.md`: markers, paths, calibration, and error bars.
- `references/raster-extraction.md`: embedded images, line/scatter/bar
  digitization, heatmaps, and colorbars.
- `references/schema.md`: normalized CSV and metadata contract.

The optional helper is
`scripts/extract_reference_data.py`. Preserve its scientific outputs as
`reference_data.csv`, `metadata.json`, and applicable validation overlays. It
must remain usable without SimFlow MCP, and no fixed helper is required when a
better source-specific method is available.
