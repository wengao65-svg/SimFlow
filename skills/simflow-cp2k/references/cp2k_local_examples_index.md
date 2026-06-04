# CP2K Optional Source-Tree Index

Use this reference only when the user provides a local CP2K source tree or an environment variable such as `CP2K_SOURCE_DIR` or `CP2K_ROOT`. Most users can prepare inputs from official documentation and portable example patterns, so prefer `cp2k_example_patterns.md` unless a source tree is explicitly available. Treat `$CP2K_SOURCE_DIR` below as the resolved source root. Do not assume maintainer-specific paths, and do not copy large example trees into SimFlow artifacts.

## Documentation folders

- `$CP2K_SOURCE_DIR/docs/getting-started`
- `$CP2K_SOURCE_DIR/docs/methods/dft`
- `$CP2K_SOURCE_DIR/docs/methods/optimization`
- `$CP2K_SOURCE_DIR/docs/methods/sampling`
- `$CP2K_SOURCE_DIR/docs/methods/properties`
- `$CP2K_SOURCE_DIR/docs/methods/qm_mm`
- `$CP2K_SOURCE_DIR/docs/methods/semiempiricals`
- `$CP2K_SOURCE_DIR/docs/methods/machine_learning`
- `$CP2K_SOURCE_DIR/docs/technologies`

## Data folders

- `$CP2K_SOURCE_DIR/data`
- `$CP2K_SOURCE_DIR/data/xc_section`
- `$CP2K_SOURCE_DIR/data/forcefield_section`
- `$CP2K_SOURCE_DIR/data/DFTB`
- `$CP2K_SOURCE_DIR/data/DeePMD`
- `$CP2K_SOURCE_DIR/data/NequIP`
- `$CP2K_SOURCE_DIR/data/NNP`

Record library names and provenance only. Do not reproduce basis/potential/library file contents in reports.

## Benchmark examples

Useful benchmark paths observed in the local tree:

- Quickstep water scaling: `$CP2K_SOURCE_DIR/benchmarks/QS`
- CI water MD: `$CP2K_SOURCE_DIR/benchmarks/CI/H2O-32_md.inp`, `H2O-128_md.inp`, `H2O-512_md.inp`
- OT low-scaling water: `$CP2K_SOURCE_DIR/benchmarks/QS_ot_ls`
- Single-node DFT, DFTB, hybrid, GW, MP2 examples: `$CP2K_SOURCE_DIR/benchmarks/QS_single_node`
- Reference DFT/hybrid/GAPW examples: `$CP2K_SOURCE_DIR/benchmarks/QS_reference`
- Hybrid LiH: `$CP2K_SOURCE_DIR/benchmarks/QS_LiH_HFX`
- MP2/RPA water: `$CP2K_SOURCE_DIR/benchmarks/QS_mp2_rpa`
- Low-scaling post-HF: `$CP2K_SOURCE_DIR/benchmarks/QS_low_scaling_postHF`
- QMMM examples: `$CP2K_SOURCE_DIR/benchmarks/QMMM_MQAE`, `QMMM_ClC`, `QMMM_CBD_PHY`
- xTB benchmark: `$CP2K_SOURCE_DIR/benchmarks/QS_stmv/stmv_xtb.inp`

Use these as patterns to inspect, not as templates to blindly copy. Benchmark files often optimize performance or regression coverage rather than the user's scientific protocol.

## Test examples

The CP2K test suite is broad and can help locate example sections:

- DFT and Quickstep: `$CP2K_SOURCE_DIR/tests/QS`
- Geometry/path workflows: `$CP2K_SOURCE_DIR/tests/NEB`
- QMMM: `$CP2K_SOURCE_DIR/tests/QMMM`
- Path integrals: `$CP2K_SOURCE_DIR/tests/Pimd`
- Semiempirical and xTB: `$CP2K_SOURCE_DIR/tests/xTB`
- DFTB: `$CP2K_SOURCE_DIR/tests/DFTB`
- Force-field/FIST: `$CP2K_SOURCE_DIR/tests/Fist`
- Machine-learning potentials: `$CP2K_SOURCE_DIR/tests/NNP`

When using tests as examples, report the user-provided source path and explain whether it is a regression test, benchmark, or tutorial-like example.
