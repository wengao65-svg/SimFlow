# LAMMPS Force Fields And MLP Deployment

Force-field choice is scientific evidence, not just syntax. Record provenance
for every potential or model path without copying restricted content.

## Classical And Reactive Potentials

Record:

- pair style and pair coefficients.
- potential file paths, hashes when allowed, source citation or repository.
- intended elements, unit convention, cutoff/mixing assumptions, charge model.
- validation benchmark from literature or user evidence.

Common risks:

- ReaxFF/COMB often need charge-equilibration review.
- EAM/MEAM/Tersoff/SW/AIREBO files are not interchangeable across elements or units.
- Long-range electrostatics require `kspace_style` and compatible boundary choices.
- Absolute or private potential paths should be recorded as metadata, not published blindly.

## MLP-MD Deployment

`simflow-lammps` only checks deployment evidence:

- MLP pair style: DeepMD, MACE, NequIP, Allegro, PACE, SNAP, QUIP, ML-IAP, or project-specific plugin.
- model file path, existence, size, hash, and source.
- element/type mapping from LAMMPS atom types to model species.
- installed LAMMPS package/plugin evidence, preferably user-provided `lmp -h` output.
- accelerator suffix/package settings when GPU/KOKKOS/OPENMP/INTEL paths are used.
- smoke-test configuration and restart/dump plan before any production claim.

Do not claim training quality, validation coverage, extrapolation safety, active-learning closure,
or production readiness. Handoff those requirements to `simflow-mlp`.

## Artifact Boundary

Acceptable artifacts include model metadata, checksums, deployment manifests,
and user-provided validation summaries. Do not vendor proprietary model or
potential file contents unless the user explicitly provides a redistribution-safe path.
