# VASP Calculation Class: Structure Optimization

Use this reference for ionic relaxation, cell relaxation, volume relaxation, equation-of-state scans, and Pulay-stress review.

## Official sources

- Structure optimization: https://www.vasp.at/wiki/Structure_optimization
- Volume relaxation: https://www.vasp.at/wiki/Volume_relaxation
- Pulay stress: https://www.vasp.at/wiki/Pulay_stress
- IBRION: https://www.vasp.at/wiki/IBRION
- ISIF: https://www.vasp.at/wiki/ISIF
- EDIFFG: https://www.vasp.at/wiki/EDIFFG
- Bulk tutorial: https://www.vasp.at/tutorials/latest/bulk/

## Minimum evidence

- Static-style input set plus explicit relaxation target: atoms only, cell shape, volume, slab layers, molecular geometry, or equation-of-state points.
- Initial structure provenance and whether selective dynamics or constraints are intended.
- Force/stress convergence target and downstream use of `CONTCAR`.

## Tags and files to inspect

- `NSW`, `IBRION`, `ISIF`, `EDIFFG`, `POTIM`, `EDIFF`, `ENCUT`, `ISMEAR`, `SIGMA`, `LREAL`, `LASPH`.
- `Selective dynamics` flags in `POSCAR`.
- Final `CONTCAR`, forces, stress, number of ionic steps, and stop reason.

## SimFlow guidance

- Preserve original user structure and write generated variants to named output directories.
- Record whether a relaxation stopped because it converged or because `NSW` was exhausted.
- For energy comparisons, ensure comparable settings, volumes/cells, smearing, k meshes, and pseudopotentials.
- For equation-of-state or volume scans, register each structure/energy pair and fit script as artifacts.

## Common risks

- Relaxing slab vacuum or constrained layers unintentionally.
- Comparing energies from different `ISIF`, k mesh, or smearing regimes.
- Treating an unconverged `CONTCAR` as a final structure.
- Pulay stress from insufficient basis cutoff during cell/volume changes.
