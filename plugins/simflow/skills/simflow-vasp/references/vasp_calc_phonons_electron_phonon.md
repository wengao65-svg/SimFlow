# VASP Calculation Class: Phonons and Electron-Phonon Work

Use this reference for finite-displacement phonons, DFPT phonons, phonon DOS/dispersion, vibrational analysis, electron-phonon coupling, phonon-limited transport, and bandgap renormalization.

## Official sources

- Phonons from finite differences: https://www.vasp.at/wiki/Phonons_from_finite_differences
- Phonons from density-functional perturbation theory: https://www.vasp.at/wiki/Phonons_from_density-functional-perturbation_theory
- Computing phonon dispersion and DOS: https://www.vasp.at/wiki/Computing_the_phonon_dispersion_and_DOS
- How to handle imaginary phonon modes: https://www.vasp.at/wiki/How_to_handle_imaginary_phonon_modes
- Phonon tutorials: https://www.vasp.at/tutorials/latest/phonons/
- Electron-phonon tutorials: https://www.vasp.at/tutorials/latest/electron-phonon/
- Bandgap renormalization due to electron-phonon coupling: https://www.vasp.at/wiki/Bandgap_renormalization_due_to_electron-phonon_coupling

## Minimum evidence

- Well-relaxed structure and force convergence suitable for vibrational analysis.
- Finite-displacement supercell plan, DFPT plan, or external-tool workflow.
- q-point/k-point convergence assumptions and non-analytical correction intent when relevant.
- External tool provenance for phonopy, py4vasp, phelel, pymatgen, ASE, or custom scripts.

## Tags and files to inspect

- `IBRION`, `NFREE`, `POTIM`, `LEPSILON`, `LPEAD`, `EDIFF`, `EDIFFG`, `ISIF`, `NSW`.
- Force outputs, displaced structures, `FORCE_CONSTANTS`/tool outputs, phonon band/DOS data.
- Electron-phonon: workflow-specific tags/files, dense sampling evidence, and transport/renormalization settings.

## SimFlow guidance

- Do not infer dynamical stability from incomplete displacement sets or underconverged forces.
- Record imaginary modes as warnings requiring structural/supercell/q-point review, not automatically as physical instabilities.
- Register displacement manifests, force directories, force-constant files, plotting scripts, and figures as artifacts.
- For electron-phonon claims, record all sampling and statistical/convergence evidence.

## Common risks

- Too small supercell or loose force convergence.
- Acoustic sum rule/symmetry handling not recorded.
- Mixing structures relaxed at different settings.
- Overinterpreting imaginary modes without checking convergence and structure.
