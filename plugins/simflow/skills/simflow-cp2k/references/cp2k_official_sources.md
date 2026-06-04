# CP2K Official Sources

Use official CP2K sources for parameter meanings, workflow claims, and examples. Prefer the CP2K version that matches the user calculation. For ordinary use, pair this reference with `cp2k_example_patterns.md`; do not require a local CP2K source tree or local CP2K executable.

## Online sources

- CP2K 2026.1 manual index: `https://manual.cp2k.org/cp2k-2026_1-branch/`
- CP2K 2026.1 input reference: `https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/`
- `GLOBAL`: `https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/GLOBAL.html`
- `FORCE_EVAL`: `https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL.html`
- `FORCE_EVAL/DFT`: `https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/FORCE_EVAL/DFT.html`
- `MOTION`: `https://manual.cp2k.org/cp2k-2026_1-branch/CP2K_INPUT/MOTION.html`
- CP2K howto static calculation: `https://www.cp2k.org/howto:static_calculation`
- CP2K exercises index: `https://www.cp2k.org/exercises`
- CP2K basis-set overview: `https://www.cp2k.org/basis_sets`
- CP2K basis-set tool: `https://www.cp2k.org/tools:cp2k-basis`

When browsing is available, verify the branch/version and include URLs in artifact metadata. When browsing is not available, use the portable examples in `cp2k_example_patterns.md` and state any unresolved official-source uncertainty.

## Optional local source-tree docs

If the user explicitly provides a local CP2K source tree, use `$CP2K_SOURCE_DIR` below as a placeholder for the resolved root. Search these files only as an optional mirror/example source, not as a default requirement:

- `$CP2K_SOURCE_DIR/docs/getting-started/first-calculation.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/index.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/gpw.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/gapw.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/basis_sets.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/pseudopotentials.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/cutoff.md`
- `$CP2K_SOURCE_DIR/docs/methods/dft/k-points.md`
- `$CP2K_SOURCE_DIR/docs/methods/optimization/geometry.md`
- `$CP2K_SOURCE_DIR/docs/methods/optimization/nudged_elastic_band.md`
- `$CP2K_SOURCE_DIR/docs/methods/sampling/molecular_dynamics.md`
- `$CP2K_SOURCE_DIR/docs/methods/sampling/langevin_dynamics.md`
- `$CP2K_SOURCE_DIR/docs/methods/sampling/metadynamics.md`
- `$CP2K_SOURCE_DIR/docs/methods/sampling/path_integrals.md`
- `$CP2K_SOURCE_DIR/docs/methods/qm_mm/index.md`
- `$CP2K_SOURCE_DIR/docs/methods/qm_mm/builtin.md`
- `$CP2K_SOURCE_DIR/docs/methods/semiempiricals/dftb.md`
- `$CP2K_SOURCE_DIR/docs/methods/semiempiricals/xtb.md`
- `$CP2K_SOURCE_DIR/docs/methods/machine_learning/deepmd.md`
- `$CP2K_SOURCE_DIR/docs/methods/machine_learning/nequip.md`
- `$CP2K_SOURCE_DIR/docs/methods/properties/infrared.md`
- `$CP2K_SOURCE_DIR/docs/methods/properties/nmr.md`
- `$CP2K_SOURCE_DIR/docs/methods/properties/raman.md`
- `$CP2K_SOURCE_DIR/docs/methods/properties/bandstructure_gw.md`

Some local docs are placeholders that point to cp2k.org howtos. If a local doc is sparse, follow the linked official howto or inspect user-provided local tests and benchmarks for example patterns.

## Input-reference anchors

Use the manual input reference when checking exact keyword names, defaults, units, and allowed values:

- `GLOBAL/RUN_TYPE`, `GLOBAL/PROJECT`, `GLOBAL/PRINT_LEVEL`
- `FORCE_EVAL/METHOD`
- `FORCE_EVAL/DFT/BASIS_SET_FILE_NAME`
- `FORCE_EVAL/DFT/POTENTIAL_FILE_NAME`
- `FORCE_EVAL/DFT/QS/EPS_DEFAULT`
- `FORCE_EVAL/DFT/QS/EXTRAPOLATION`
- `FORCE_EVAL/DFT/MGRID/CUTOFF`
- `FORCE_EVAL/DFT/MGRID/REL_CUTOFF`
- `FORCE_EVAL/DFT/SCF/EPS_SCF`
- `FORCE_EVAL/DFT/SCF/MAX_SCF`
- `FORCE_EVAL/DFT/SCF/SCF_GUESS`
- `FORCE_EVAL/DFT/SCF/OT`
- `FORCE_EVAL/DFT/SCF/OUTER_SCF`
- `FORCE_EVAL/DFT/XC/XC_FUNCTIONAL`
- `FORCE_EVAL/SUBSYS/CELL`
- `FORCE_EVAL/SUBSYS/TOPOLOGY`
- `FORCE_EVAL/SUBSYS/KIND`
- `MOTION/GEO_OPT`
- `MOTION/CELL_OPT`
- `MOTION/MD`
- `MOTION/PRINT/TRAJECTORY`
- `EXT_RESTART`

## Evidence rules

- Cite official URLs or local source-tree paths in reports when parameter advice or workflow claims matter.
- Record the CP2K version or branch whenever it can be inferred from logs, executable output, docs, or user input.
- Do not copy large CP2K docs, basis libraries, potential libraries, benchmark trees, maintainer-private paths, or local install paths into artifacts or distributable skill docs. Summarize and reference official URLs or user-provided paths only when needed.
