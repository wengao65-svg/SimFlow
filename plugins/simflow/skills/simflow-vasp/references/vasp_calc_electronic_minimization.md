# VASP Calculation Class: Electronic Minimization and Static SCF

Use this reference for static ground-state calculations, molecule or bulk setup checks, fixed-structure SCF, charge-density generation, and dry-run setup review.

## Official sources

- Setting up an electronic minimization: https://www.vasp.at/wiki/Setting_up_an_electronic_minimization
- Command-line arguments and dry runs: https://www.vasp.at/wiki/Command-line_arguments
- Bulk tutorial: https://www.vasp.at/tutorials/latest/bulk/
- Molecules tutorial: https://www.vasp.at/tutorials/latest/molecules/
- INCAR: https://www.vasp.at/wiki/INCAR
- KPOINTS: https://www.vasp.at/wiki/KPOINTS
- POTCAR: https://www.vasp.at/wiki/POTCAR

## Minimum evidence

- `POSCAR`, `INCAR`, `KPOINTS`, and licensed local `POTCAR` metadata.
- Purpose of the static run: total energy, charge density for a downstream run, reference state, molecule/bulk benchmark, or dry-run inspection.
- VASP version/executable family and pseudopotential flavor/date metadata when available.

## Tags and files to inspect

- `ENCUT`, `EDIFF`, `NELM`, `ALGO`, `ISMEAR`, `SIGMA`, `ISPIN`, `MAGMOM`, `LREAL`, `LASPH`, `PREC`, `LWAVE`, `LCHARG`.
- K-point mesh density and Gamma/Monkhorst choice.
- Output evidence from `OUTCAR`, `OSZICAR`, `vasprun.xml`, or `vaspout.h5`.

## SimFlow guidance

- Default to dry-run/static inspection unless the user explicitly requests real execution and approval gates pass.
- Do not infer convergence from file existence or scheduler completion.
- For downstream DOS/band/SOC/hybrid/GW/BSE work, record whether `CHGCAR`, `WAVECAR`, `vaspout.h5`, and Fermi-level evidence are needed.
- Register input manifests, validation reports, dry-run reports, and helper-run manifests as artifacts.

## Common risks

- Incompatible pseudopotential families or element order mismatch.
- Smearing choices reused across incompatible tasks.
- Insufficient k-point/ENCUT convergence for quantitative energy differences.
- Missing magnetic initialization for potentially magnetic systems.
