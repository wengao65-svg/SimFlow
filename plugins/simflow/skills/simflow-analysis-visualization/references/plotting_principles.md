# Plotting Principles

Use this reference when a task asks for publication figures, figure cleanup,
plotting style, figure manifests, or visual evidence for writing and handoff.

## Figure contract

- Every figure should trace back to source data, a script or notebook, the command or parameters used, and an environment note.
- Save derived data separately from rendered images when the plotted values are not directly present in the raw output.
- Prefer script-reproducible styling over manual edits. If a manual edit is unavoidable, record what changed and keep it out of quantitative interpretation.
- Distinguish exploratory plots, review drafts, and final publication figures in the artifact metadata or figure manifest.

## Matplotlib route

- Prefer Matplotlib's object-oriented interface for reusable or multi-panel figures so axes, scales, legends, and annotations are explicit.
- Use style sheets or local `rcParams` for consistent fonts, line widths, tick sizes, and color cycles. Keep style choices in the plotting script or a recorded style file.
- Use `Agg` or another noninteractive backend for automated runs on headless systems.
- For final figures, export a vector format such as PDF or SVG when the plot is line art, and export high-resolution PNG or TIFF when raster output is required.
- Keep figure dimensions, units, axis labels, legends, colorbars, and panel labels explicit. Record unit conversions in the script or derived-data metadata.

## Scientific figure checks

- Axes should include units and clear quantity names. Do not rely on captions to repair missing axis metadata.
- Captions should state the source calculation or dataset, analysis window, normalization or fitting choice, and uncertainty convention when relevant.
- Use color maps and palettes that remain legible in grayscale or for common color-vision differences. Avoid color as the only carrier of a scientific category.
- For multi-panel figures, keep panel order tied to a scientific question or workflow order, not merely script output order.
- Avoid smoothing, interpolation, clipping, offsetting, or baseline subtraction unless it is scientifically justified and recorded.

## Provenance and handoff

- A figure manifest should include figure path, source data path, plotting script path, parent artifact ids, software/tool versions when available, and skipped or warning states.
- Captions are artifacts when they are intended for writing or handoff. Link them to the figure and analysis artifacts they interpret.
- If a figure cannot be regenerated because an optional dependency is missing, record a skipped reason and preserve the available intermediate data.

## Useful external references

- Matplotlib quick start and object-oriented plotting: https://matplotlib.org/stable/users/explain/quick_start.html
- Matplotlib style sheets and rcParams: https://matplotlib.org/stable/users/explain/customizing.html
- Matplotlib cheat sheets: https://matplotlib.org/cheatsheets/
- Scientific Visualization: Python + Matplotlib: https://github.com/rougier/scientific-visualization-book
