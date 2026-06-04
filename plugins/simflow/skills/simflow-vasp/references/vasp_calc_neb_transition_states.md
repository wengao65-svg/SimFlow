# VASP Calculation Class: NEB and Transition States

Use this reference for NEB, climbing-image NEB, dimer, IRC, static transition-state searches, and dynamic transition-state workflows.

## Official sources

- Nudged elastic bands: https://www.vasp.at/wiki/Nudged_elastic_bands
- Transition states tutorial: https://www.vasp.at/tutorials/latest/transition_states/
- Practical guide to transition-state finding: https://www.vasp.at/wiki/Practical_considerations_for_transition_state_finding_calculations
- Improved dimer method: https://www.vasp.at/wiki/Improved_dimer_method
- Intrinsic reaction coordinate calculations: https://www.vasp.at/wiki/Intrinsic-reaction-coordinate_calculations
- IMAGES: https://www.vasp.at/wiki/IMAGES
- ICHAIN: https://www.vasp.at/wiki/ICHAIN

## Minimum evidence

- Converged initial and final states, same atom count/order, and clear reaction coordinate.
- Image directories (`00`, `01`, ...) and image-generation method.
- Consistent `POTCAR` metadata, `KPOINTS`, and constraints across images.
- Barrier convergence criteria and whether climbing image is intended.

## Tags and files to inspect

- `IMAGES`, `IBRION`, `POTIM`, `SPRING`, `LCLIMB`, `NSW`, `EDIFFG`, `ISIF`.
- Per-image `POSCAR`/`CONTCAR`, `OUTCAR`, `OSZICAR`, forces, energies, and warnings.
- For dimer/IRC workflows, inspect method-specific tags and endpoint continuity.

## SimFlow guidance

- Do not record a transition state or barrier as final until every relevant image is converged and the path is chemically sensible.
- Register endpoint structures, image manifest, interpolation method, validation report, barrier table, and plot script as artifacts.
- Start with minimal images when the path is uncertain; add images only with a documented rationale.
- Preserve all user-provided image directories.

## Common risks

- Atom ordering changes between endpoints/images.
- Images crossing, collapsing, or following an unintended path.
- Endpoint structures not relaxed under the same settings.
- Barrier reported from unconverged or force-inconsistent images.
