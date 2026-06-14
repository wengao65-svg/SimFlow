# GPUMD Selected Output Parsing

Supported parsing should remain conservative:

- Parse simple whitespace-delimited numeric tables and record row count, column count, final row, and numeric min/max ranges.
- Recognize common filenames such as `thermo.out`, `loss.out`, `msd.out`, `rdf.out`, `hac.out`, `kappa.out`, and `dos.out` as file roles, but do not claim full semantic coverage.
- Preserve raw file paths, hashes, parser assumptions, skipped files, and parser warnings.
- Report unsupported or malformed files as unparsed evidence instead of guessing.

Do not compute final transport coefficients, model fitness, convergence status, or publication claims without an explicit analysis method and validation evidence.
