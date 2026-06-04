# VASP Calculation Class: DOS and Band Structures

Use this reference for total/projected DOS, non-SCF DOS, DFT band structures, hybrid band structures, and figure lineage.

## Official sources

- DFT band structure how-to: https://www.vasp.at/wiki/Band-structure_calculation_using_density-functional_theory
- Hybrid band structure how-to: https://www.vasp.at/wiki/Band-structure_calculation_using_hybrid_functionals
- KPOINTS: https://www.vasp.at/wiki/KPOINTS
- KPOINTS_OPT: https://www.vasp.at/wiki/KPOINTS_OPT
- DOSCAR: https://www.vasp.at/wiki/DOSCAR
- EIGENVAL: https://www.vasp.at/wiki/EIGENVAL
- LORBIT: https://www.vasp.at/wiki/LORBIT
- Bulk tutorial: https://www.vasp.at/tutorials/latest/bulk/

## Minimum evidence

- A converged predecessor calculation and charge/orbital evidence appropriate to the method.
- For DFT split-run bands: compatible `CHGCAR`; for hybrid bands: a regular k mesh and usually `WAVECAR`/orbital provenance.
- High-symmetry path source and coordinate convention.
- Fermi energy source used for plotting.

## Tags and files to inspect

- `ICHARG`, `LORBIT`, `NEDOS`, `ISMEAR`, `SIGMA`, `EFERMI`, `LMAXMIX`, `KPOINTS`, `KPOINTS_OPT`.
- `CHGCAR`, `WAVECAR`, `EIGENVAL`, `DOSCAR`, `vaspout.h5`, `vasprun.xml`, `OUTCAR`.
- For hybrid band structures, inspect `LHFCALC`, `HFSCREEN`, `HFRCUT`, and zero-weight/k-points strategy.

## SimFlow guidance

- Record whether the figure came from py4vasp, VASPKIT, SimFlow parser, pymatgen, ASE, or custom Python.
- Record axis limits, Fermi-level shift, spin/SOC projection choices, orbital projections, and plotted data files.
- Do not use line-mode k points to compute a reliable Fermi energy; use the SCF source.
- For DFT+U band structures, record `LMAXMIX` treatment and U/J provenance.

## Common risks

- Missing or incompatible `CHGCAR`/`WAVECAR`.
- Confusing a line-mode Fermi energy with the SCF Fermi energy.
- Over-interpreting metallic band gaps.
- Treating a hybrid band workflow like a fixed-density DFT NSCF run.
