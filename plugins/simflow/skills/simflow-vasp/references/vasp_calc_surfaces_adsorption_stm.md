# VASP Calculation Class: Surfaces, Adsorption, Work Functions, and STM

Use this reference for slab models, adsorption workflows, work functions, dipole corrections, surface STM simulation, and partial charge density visualizations.

## Official sources

- Surfaces tutorial: https://www.vasp.at/tutorials/latest/surfaces/
- Partial charge densities and STM simulations: https://www.vasp.at/wiki/Partial_charge_densities_and_STM_simulations
- Computing the work function: https://www.vasp.at/wiki/Computing_the_work_function
- LDIPOL: https://www.vasp.at/wiki/LDIPOL
- IDIPOL: https://www.vasp.at/wiki/IDIPOL
- Dipole corrections for defects in solids: https://www.vasp.at/wiki/Dipole_corrections_for_defects_in_solids
- LPARD: https://www.vasp.at/wiki/LPARD

## Minimum evidence

- Slab construction method, Miller index, termination, thickness, vacuum, relaxed layers, and reference bulk.
- Adsorbate structure, adsorption site(s), coverage, spin/charge state, reference energy definitions, and dispersion correction choices.
- Work-function or STM post-processing plan and electrostatic potential/partial charge evidence.

## Tags and files to inspect

- `ISIF`, selective dynamics flags, `LDIPOL`, `IDIPOL`, `DIPOL`, `LVHAR`, `LVTOT`, `LPARD`, `EINT`, `IBAND`, `NBMOD`, `KPUSE`.
- `LOCPOT`, `PARCHG`, `CHGCAR`, `WAVECAR`, `vaspout.h5`, potential profiles, and plotted data.

## SimFlow guidance

- Preserve all user-provided slabs/adsorbates and write variants under named directories.
- Record vacuum and dipole-correction choices; asymmetric slabs and charged surfaces need extra care.
- For adsorption energies, register all reference calculations with comparable settings.
- For STM/partial charges, record selected bands/energy window, bias interpretation, and visualization tool.

## Common risks

- Inadequate vacuum or slab thickness.
- Comparing adsorption energies with inconsistent reference states.
- Missing dipole correction for asymmetric slabs.
- STM images generated from an undocumented band/energy window.
