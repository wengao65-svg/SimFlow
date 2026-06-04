# VASP Calculation Class: Wannier, Partial Charges, and Post-processing

Use this reference for Wannierization, band interpolation handoff, band-decomposed charge density, STM post-processing, py4vasp analysis, VASPKIT workflows, and custom parser scripts.

## Official sources

- Constructing Wannier orbitals: https://www.vasp.at/wiki/Constructing_Wannier_orbitals
- Partial charge densities and STM simulations: https://www.vasp.at/wiki/Partial_charge_densities_and_STM_simulations
- py4vasp documentation: https://www.vasp.at/py4vasp/latest/
- vaspout.h5: https://www.vasp.at/wiki/Vaspout.h5
- PARCHG: https://www.vasp.at/wiki/PARCHG
- LPARD: https://www.vasp.at/wiki/LPARD
- LWANNIER90: https://www.vasp.at/wiki/LWANNIER90

## Minimum evidence

- Converged predecessor and output files needed by the selected post-processing path.
- Tool choice: py4vasp, Wannier90, VASPKIT, pymatgen, ASE, SimFlow parser, notebook, or custom script.
- Selection definitions: bands, k points, energy window, projections, orbitals, atoms, and spin/SOC channels.

## Tags and files to inspect

- Wannier: `LWANNIER90`, `LOCPROJ`, `LSCDM`, projection windows, `WAVECAR`, `vaspout.h5`.
- Partial charges: `LPARD`, `NBMOD`, `IBAND`, `EINT`, `KPUSE`, `PARCHG`, `WAVECAR`.
- Plot scripts, notebooks, generated data tables, and environment manifests.

## SimFlow guidance

- Register post-processing scripts and raw extracted data, not just final images.
- Record exact input/output files, tool versions, and selection parameters.
- Do not treat post-processing artifacts as new first-principles results unless the calculation evidence is present.
- For external tools, record command lines and any generated intermediate files.

## Common risks

- Partial charges selected from undocumented bands or energy windows.
- Wannier projections/window choices not recorded.
- Missing `vaspout.h5` or incompatible py4vasp version.
- Figures that cannot be traced back to exact raw VASP files.
