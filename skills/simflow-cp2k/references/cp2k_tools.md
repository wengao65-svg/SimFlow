# CP2K Tools

CP2K does not have a dedicated third-party pre/post-processing toolkit
equivalent to VASPKIT or GPUMDkit. Structure I/O, parsing, and analysis
rely on general-purpose tools. For general tool guidance (ASE, pymatgen,
Matplotlib, pandas, custom Python parsers), see
`simflow-analysis-visualization/references/tooling_index.md`.

This file records CP2K-specific tool routes so the agent knows where to
look before falling back to generic tools.

## ASE CP2K calculator interface

ASE provides a CP2K calculator interface for structure I/O and
single-point, geometry optimization, or MD tasks driven from Python.

- Capabilities: structure I/O, CP2K input generation via ASE's CP2K
  calculator, single-point energy/force/stress queries, geometry
  optimization driver, simple MD driver.
- ASE is a general tool; see `tooling_index.md` for ASE's general
  capabilities (format conversion, trajectory handling, geometry
  operations).
- SimFlow context: record ASE version, CP2K calculator configuration,
  structure provenance, and any ASE-generated CP2K input files.
- Limitations: ASE's CP2K calculator exposes a limited subset of CP2K
  keywords; advanced sections (`MOTION/MD`, `SCF` details, `KIND` basis
  assignments) usually require hand-edited input decks or SimFlow's
  `generate_cp2k_inputs.py` helper.

## CP2K bundled utilities

The CP2K distribution includes utility scripts for basis set and
potential inspection, restart handling, and output conversion.

- Refer to the user's CP2K source tree or installation's `tools/` and
  `data/` directories for available utilities and basis/potential
  libraries.
- Common utilities include basis set converters, potential file
  inspectors, and restart extraction helpers.
- SimFlow context: record utility path, version, command, input/output
  files, and provenance.
- Do not copy CP2K basis libraries, potential libraries, benchmark
  trees, or large source-tree content into reports or distributable
  skill docs. See `cp2k_official_sources.md` for official documentation
  entry points instead.

## Custom parsers and notebooks

For CP2K output formats (`.out`, `.log`, `.ener`, `*-pos-*.xyz`,
`*-frc-*.xyz`, `.restart`, cell files, user-defined print outputs) that
exceed the common parser surface, use custom Python, pandas, notebooks,
shell tools, or SimFlow's `parse_cp2k_outputs.py` helper. Record parser,
inputs, outputs, and limitations explicitly.
