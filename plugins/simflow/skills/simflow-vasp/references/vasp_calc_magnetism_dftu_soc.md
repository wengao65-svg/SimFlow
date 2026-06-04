# VASP Calculation Class: Magnetism, DFT+U, SOC, and Noncollinear Work

Use this reference for spin-polarized calculations, magnetic energy comparisons, DFT+U, noncollinear magnetism, SOC, magnetic anisotropy, and spin spirals.

## Official sources

- Magnetism tutorials: https://www.vasp.at/tutorials/latest/magnetism/
- ISPIN: https://www.vasp.at/wiki/ISPIN
- MAGMOM: https://www.vasp.at/wiki/MAGMOM
- DFT+U category: https://www.vasp.at/wiki/DFT%2BU
- LDAU: https://www.vasp.at/wiki/LDAU
- LDAUU: https://www.vasp.at/wiki/LDAUU
- LSORBIT: https://www.vasp.at/wiki/LSORBIT
- LNONCOLLINEAR: https://www.vasp.at/wiki/LNONCOLLINEAR
- SAXIS: https://www.vasp.at/wiki/SAXIS
- Spin spirals: https://www.vasp.at/wiki/Spin_spirals

## Minimum evidence

- Magnetic state intent: nonmagnetic, ferromagnetic, antiferromagnetic, ferrimagnetic, noncollinear, SOC, anisotropy, or spin spiral.
- Initial `MAGMOM` pattern and whether multiple magnetic initial states were tested.
- U/J values, target orbitals, and source/provenance for every DFT+U decision.
- Executable family for SOC/noncollinear work, especially `vasp_ncl`.

## Tags and files to inspect

- `ISPIN`, `MAGMOM`, `LORBIT`, `LORBMOM`, `LDAU`, `LDAUTYPE`, `LDAUL`, `LDAUU`, `LDAUJ`, `LMAXMIX`.
- `LSORBIT`, `LNONCOLLINEAR`, `SAXIS`, `ISYM`, `GGA_COMPAT`, `ICHARG`.
- Site/orbital moments, total magnetization, SOC energy terms, and symmetry information in outputs.

## SimFlow guidance

- Treat different magnetic orderings, U/J settings, pseudopotentials, and SOC/non-SOC setups as different Hamiltonians unless explicitly justified.
- For SOC energy differences, record k-point convergence and symmetry choices; energy scales can be very small.
- Do not compare total energies across different U/J values as if only structure changed.
- Register magnetic-state matrices, U/J provenance notes, convergence studies, and output summaries as artifacts.

## Common risks

- Single initial magnetic state mistaken for the ground magnetic order.
- SOC restart with incompatible k-point set or symmetry.
- Missing `LMAXMIX` review for DFT+U fixed-density workflows.
- Unrecorded U/J source leading to irreproducible conclusions.
