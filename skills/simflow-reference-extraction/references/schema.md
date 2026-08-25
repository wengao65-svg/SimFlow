# Normalized dataset contract — schema 0.3

Each extracted dataset should include:

- `reference_data.csv` containing normalized numerical/tabular values;
- `metadata.json` containing source identity, semantics, provenance, extraction method, calibration, and review status;
- source coordinates for figure-derived data when practical;
- validation artifacts for reconstructed figures;
- optionally `validation_report.json` produced by `dataset-validate`.

Recommended metadata shape:

```json
{
  "schema_version": "0.3",
  "dataset_id": "stable_dataset_identifier",
  "paper": {
    "title": null,
    "authors": [],
    "year": null,
    "doi": null,
    "arxiv_id": null
  },
  "source": {
    "input_type": "source_file|arxiv_source|publisher_pdf|figure_file",
    "source_file": "...",
    "source_sha256": "...",
    "page": null,
    "panel": null
  },
  "quantity": {
    "name": "Reported quantity",
    "conditions": {}
  },
  "series": [],
  "extraction": {
    "provenance_grade": "A0|A1|A2|B1|B2|C1|C2",
    "method": "...",
    "calibration": {},
    "notes": []
  },
  "quality": {
    "status": "verified|needs_review",
    "checks": []
  },
  "outputs": {
    "csv": "reference_data.csv"
  }
}
```

## Figure-derived CSV fields

Vector path datasets generally include:

- series name;
- source order;
- calibrated x/y values;
- `pdf_x_pt`, `pdf_y_pt`;
- source drawing index.

Vector marker datasets may additionally include:

- marker drawing index;
- matched error-bar drawing index;
- `y_low`, `y_high`, `yerr_minus`, `yerr_plus`.

Raster line/scatter/bar datasets generally include:

- calibrated x/y values;
- `pixel_x`, `pixel_y`;
- a mode-specific auxiliary field.

Raster heatmap datasets generally include:

- calibrated x/y values;
- mapped scalar value;
- source pixel coordinates;
- Lab-space color distance;
- a `valid` flag indicating whether the source color was acceptably close to the calibrated colorbar.

## Transformation rule

Do not silently resample, smooth, extrapolate, interpolate, unit-convert, or fill missing/occluded data. If a transformed dataset is useful, create a separate output and record the transformation method and parameters.
