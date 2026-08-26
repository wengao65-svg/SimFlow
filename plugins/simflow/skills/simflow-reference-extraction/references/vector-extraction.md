# Vector figure extraction

Use vector extraction when target marks are represented by PDF vector drawings. Run `figure-inspect` first and inspect `figure_inspection.json`, the full preview, and the detected axes crops.

## Inspection output

For each detected Cartesian axes, v0.3 reports:

- plotting rectangle;
- major tick positions;
- candidate continuous colored paths;
- repeated small marker groups;
- candidate single vertical colored line segments that may represent y error bars.

Marker groups include both all repeated symbols and, when a long same-color path exists, a filtered `data_marker_*` subset. The filter helps remove marker symbols drawn inside legends.

## B1 — discrete vector markers

Use `vector-marker-extract` when discrete markers encode sampled values. Map semantic names with:

```text
--groups '0=Series_A,1=Series_B'
```

The command uses marker centers as source coordinates and assigns provenance B1.

If the same marker series has vertical vector error bars, add `--with-yerr`. The extractor matches same-color vertical segments at the marker x position and writes:

- `y_low` / `y_high`;
- `yerr_minus` / `yerr_plus`;
- the matched error-bar drawing index.

Always inspect the marker overlay and verify the matched bars. Horizontal-only uncertainties and complex asymmetric cap structures remain review cases unless explicitly represented by the recovered vertical segment.

## B2 — continuous vector paths

Use `vector-extract` for continuous paths. Candidate paths include drawing index, color, line width, dash pattern, item count, and bounding box.

Calibrate using visible tick values whenever possible. `--x-tick-values` pairs left-to-right values with detected x tick positions; `--y-tick-values` pairs top-to-bottom values with detected y tick positions. Manual `PDF_COORD=DATA_VALUE` anchors are also supported.

For linear axes, calibration is affine. For `log10`, calibration is fitted in log10(data) space.

Treat reconstructed vector paths as the published graphic, not automatically as author raw values. Plotting software may simplify path vertices or render interpolated/smoothed curves.

## Review cases

Escalate to review when:

- marker groups share indistinguishable geometry/color;
- legend symbols cannot be separated from data markers;
- paths are clipped or occluded;
- axes are broken/non-Cartesian;
- an error representation is a filled band rather than discrete error bars;
- the same source object combines multiple semantically distinct series.
