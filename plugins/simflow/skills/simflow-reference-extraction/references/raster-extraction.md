# Raster figure extraction

Raster extraction is built into this skill.

## Preparation

Prefer the original embedded raster object from a PDF. `raster-prepare` records image xref, pixel dimensions, page placement, hash, and provenance. Render a page/crop only when an embedded source image is unavailable or unsuitable.

## Inspection

Run `raster-inspect IMAGE --out DIR`.

It produces:

- `raster_inspection.json` with image dimensions, detected rectangular plot regions, and dominant saturated color candidates;
- `raster_inspection_overlay.png` with detected plot indices.

Automatic plot detection uses long dark horizontal/vertical axes or frame lines. Frameless, broken-axis, polar, ternary, and unusually styled plots may require a manual `--plot-bbox`.

## Line, scatter, and bar extraction

`raster-extract` supports:

- `line`: Lab-space color segmentation plus a long coherent trace across image columns;
- `scatter`: connected-component centroids for point markers;
- `bar`: centers and value-side edges of filled rectangular components.

Map series explicitly with `name=#RRGGBB` when possible. Black/gray series can be supplied explicitly. Use `--exclude-bbox` to remove legends or annotations that contaminate a mask.

Each mapped series produces a binary mask and the extraction produces `raster_overlay.png`.

## Heatmap/colorbar extraction

Use `raster-heatmap-extract` when data are encoded by color rather than discrete lines/points/bars.

Required inputs:

- heatmap pixel bounding box;
- colorbar pixel bounding box;
- colorbar minimum and maximum;
- colorbar orientation and which end contains the minimum;
- x/y calibration or exact frame bounds.

The extractor builds a colorbar lookup table, maps heatmap pixels in Lab color space, and writes:

- `reference_data.csv` in long form;
- `heatmap_reconstruction.png` showing nearest calibrated colorbar colors;
- `heatmap_color_error.png` showing color-distance mismatch.

Pixels beyond `--max-color-distance` are flagged invalid instead of being assigned an unsupported value. `--heatmap-margin` avoids axes/frame pixels; `--stride` controls spatial sampling density.

A logarithmic colorbar is supported with `--value-scale log10` and positive limits.

## Calibration

Use pixel-to-data anchors when possible:

```text
--x-cal 'PIXEL_X=VALUE,...'
--y-cal 'PIXEL_Y=VALUE,...'
```

If the plot frame exactly matches numerical limits, `--x-min/--x-max` and `--y-min/--y-max` are acceptable. `log10` axes require positive values.

## Limitations and validation

No raster method can recover data hidden by complete occlusion. Do not invent covered regions.

Always inspect the relevant overlay/reconstruction and confirm:

- extraction aligns with intended marks/colors;
- calibration and axis scale are correct;
- series/colorbar mapping is correct;
- annotations/legends are not being treated as data;
- low-resolution or compression artifacts are reflected in review status.
