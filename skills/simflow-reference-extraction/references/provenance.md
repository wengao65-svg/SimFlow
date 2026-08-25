# Provenance grades

Use the strongest available source and record one primary grade per normalized dataset.

- **A0** — author-provided raw numerical data such as CSV, DAT, JSON, NumPy, HDF5, spreadsheet, or equivalent.
- **A1** — author plotting data or code that exposes the numerical arrays used to construct the published result.
- **A2** — numerical values embedded directly in TeX tables, verbatim blocks, source text, or equivalent structured source.
- **B1** — reconstruction from discrete vector markers in PDF/SVG/EPS. Prefer when markers clearly encode sampled data points. Error-bar bounds recovered from the same vector figure remain B1 figure reconstruction.
- **B2** — reconstruction from vector paths in PDF/SVG/EPS. This reproduces the published plotted path, which may contain interpolation or path simplification.
- **C1** — digitization from an author/publisher raster figure at its original embedded resolution.
- **C2** — digitization from a rendered, scanned, screenshot, or otherwise re-rasterized page/figure.

Never describe B1/B2/C1/C2 data as author raw numerical data. Use provenance language such as `vector_marker_reconstruction`, `vector_path_reconstruction`, `raster_line_digitization`, or `raster_heatmap_colorbar_digitization`.
