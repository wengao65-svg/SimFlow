# VASP Calculation Class: Defects and Charged Systems

Use this reference for point defects, charged supercells, electrostatic corrections, potential alignment, defect formation energies, and defect-related spectroscopy.

## Official sources

- Electrostatic corrections: https://www.vasp.at/wiki/Electrostatic_corrections
- Dipole corrections for defects in solids: https://www.vasp.at/wiki/Dipole_corrections_for_defects_in_solids
- NELECT: https://www.vasp.at/wiki/NELECT
- LOCPOT: https://www.vasp.at/wiki/LOCPOT
- Preparing a super cell: https://www.vasp.at/wiki/Preparing_a_Super_Cell
- Supercell core-hole calculations: https://www.vasp.at/wiki/Supercell_core-hole_calculations

## Minimum evidence

- Pristine reference structure and defect structure provenance.
- Supercell size, defect type/site, charge state, chemical potentials, alignment/correction scheme, and reference energies.
- Spin state, U/SOC choices, and finite-size convergence plan when relevant.

## Tags and files to inspect

- `NELECT`, `LDIPOL`, `IDIPOL`, `DIPOL`, `LVHAR`, `LVTOT`, `ISPIN`, `MAGMOM`, `LDAU*`, `LMAXMIX`.
- `LOCPOT`, `CHGCAR`, `OUTCAR`, `OSZICAR`, defect/pristine `CONTCAR`, correction outputs/scripts.

## SimFlow guidance

- Never infer a formation energy from a single charged calculation without reference-state evidence.
- Record charge corrections, potential alignment, chemical potentials, and finite-size assumptions as separate artifacts.
- Do not compare different charge states or U/SOC settings without explicit formula and convention.
- Mark incomplete correction evidence as a blocker for final defect claims.

## Common risks

- Using total electron count rather than VASP valence-electron `NELECT` semantics.
- Missing potential alignment/correction for charged defects.
- Inadequate supercell size or unrelaxed defect geometry.
- Unrecorded chemical-potential convention.
