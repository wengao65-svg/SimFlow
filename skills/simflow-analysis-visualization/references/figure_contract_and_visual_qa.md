# Figure Contract And Visual QA

Use this reference when a plot is intended to support a scientific claim,
publication figure, caption, presentation, review, or handoff. The figure is
not ready until its claim, data, script, parameters, environment, output files,
and review status can be traced.

## Figure contract

Before rendering the final figure, record:

- the claim or question the figure is meant to support
- source data and parent artifact ids
- derived data paths when plotted values are not directly present in raw output
- analysis window, filtering, binning, smoothing, normalization, fitting, or
  uncertainty convention
- figure type and why it matches the data profile and claim
- target audience, journal or report context when known, output format, size,
  units, and accessibility constraints
- expected caption evidence: source calculation, method, selections, windows,
  units, and uncertainty or caveat language

If the claim is unclear, keep the figure exploratory or ask for the intended
claim before producing a publication-style result.

## Chart-selection guardrails

- Prefer distributions or point overlays over mean-only bars for small groups
  or nonnormal data.
- Avoid dual-axis plots, unexplained smoothing, rainbow color maps, truncated
  axes without annotation, and connecting categorical means as if they were
  continuous trajectories.
- Split overloaded figures when one panel is trying to support multiple
  unrelated claims.
- Use redundant encodings when color carries scientific categories, especially
  for multi-series line plots or categorical comparisons.

## Visual QA loop

For final or handoff figures, use a recorded review loop:

1. Render a preview image from the script or notebook using a headless backend
   when possible.
2. Inspect the preview for missing glyphs, clipped labels, overlapping ticks,
   unreadable legends, colorbar problems, panel-label alignment, occluded data,
   wrong units, and accidental empty panels.
3. Record any problem and the parameter, style, layout, or data-selection change
   used to fix it.
4. Re-render and re-check until the figure is accepted or marked as blocked.

The QA loop may be performed by programmatic checks, image inspection, or both.
Do not manually edit the rendered image in a way that disconnects it from the
recorded source data and script.

The optional `scripts/audit_figure.py` helper can record deterministic baseline
checks such as file existence, non-empty output, image readability, dimensions,
near-blank pixels, and alpha/background warnings. It does not prove that labels
are unclipped, legends do not overlap, units are correct, or the figure supports
the intended claim; those remain manual or multimodal review items to record in
the figure manifest.

## Figure manifest fields

A figure manifest should include:

- figure path and preview path when separate
- source data and derived data paths
- plotting script or notebook path
- command line or notebook execution note
- environment or package version note when practical
- parent artifact ids
- figure contract summary
- visual QA status and warnings
- caption path when the caption is a handoff artifact

If a dependency is missing and the figure cannot be regenerated, record the
missing dependency, skipped scope, and any preserved intermediate data.
