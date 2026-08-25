# Structured source extraction

Structured source content has priority over figure reconstruction.

## `source-manifest`

Use `source-manifest` on an archive or directory to inventory:

- raw numerical candidates (`csv`, `dat`, `json`, NumPy, HDF5, spreadsheets, and similar files);
- plotting/source-code candidates;
- TeX files, figure declarations, captions, labels, tables, and numerical verbatim blocks;
- figure files and their coarse vector/raster classification.

The manifest is discovery metadata. It does not by itself establish that every candidate file is the data behind a particular figure.

## `source-extract --kind raw`

The v0.3 normalizer supports common delimited text, JSON, NumPy, Excel, and HDF5 inputs. It preserves values without smoothing, interpolation, unit conversion, or scientific reinterpretation.

Header/delimiter inference is heuristic. Review `metadata.json` fields such as `header_detected`, `delimiter`, dataset names, and shape information.

## TeX tables and verbatim blocks

Use:

```text
--kind tex-table --table-index N
--kind tex-verbatim --verbatim-index N
```

Indices are zero-based within the TeX file. Simple `tabular` structures are normalized to CSV. Complex multirow/multicolumn layouts may require manual review because visual table structure can exceed a rectangular CSV representation.

Numerical verbatim blocks are treated as delimited/whitespace text tables. Inconsistent-width prose or separator rows may be excluded; the count is reported in metadata.

## Provenance

- Raw author numerical files normalized without alteration are A0.
- Plotting scripts/data that expose the actual plotting arrays are A1; inspect the source relationship before assigning this grade.
- Numerical TeX tables/verbatim blocks are A2.

Do not downgrade to B/C figure reconstruction when an A-level source directly answers the requested numerical question.
