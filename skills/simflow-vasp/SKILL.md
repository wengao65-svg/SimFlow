---
name: simflow-vasp
description: Provide VASP-specific guidance for input setup and review, convergence and restart diagnosis, troubleshooting, output interpretation, and licensed POTCAR metadata handling. Use when requests mention VASP, INCAR/POSCAR/KPOINTS/POTCAR, OUTCAR/OSZICAR/vasprun.xml/vaspout.h5, CHGCAR/WAVECAR, or VASP workflows such as relaxation, DOS/bands, AIMD, NEB, phonons, DFT+U/SOC/hybrids, defects, surfaces, optics, spectroscopy, or Wannier analysis.
---

# VASP Domain Skill

## Purpose

Provide VASP-specific semantics to any current Research Task Skills that need
them. This Skill does not own workflow progression, submission, approval, or
SimFlow state.

## Use when

- The task involves INCAR, POSCAR, KPOINTS, POTCAR metadata, OUTCAR, OSZICAR,
  vasprun.xml, vaspout.h5, CHGCAR, WAVECAR, DOSCAR, EIGENVAL, or VASP errors.
- VASP-specific choices affect setup, convergence, parsing, or interpretation.

## Do not use when

- The task is engine-independent and does not require VASP semantics.
- The request concerns only other software and no VASP-specific boundary is
  material.

## Domain principles

- Infer the calculation class from explicit intent and files. Do not default
  unknown VASP tasks to `static`.
- Keep scientific model choices separate from INCAR/KPOINTS syntax.
- Preserve existing validated inputs unless a change is justified.
- Distinguish process completion, electronic convergence, ionic convergence,
  and scientific adequacy.
- Prefer official VASP documentation for parameter semantics.
- Treat py4vasp, VASPKIT, pymatgen, ASE, and custom scripts as optional tools.

## Minimum checks

- POSCAR species, counts, cell, coordinates, and intended periodicity agree.
- INCAR settings are internally consistent with relaxation, MD, NEB, phonon,
  DOS/band, hybrid, SOC, DFT+U, GW/BSE/RPA, defect, or surface intent.
- KPOINTS and smearing choices match dimensionality and calculation purpose.
- Restart dependencies such as WAVECAR or CHGCAR are available and compatible.
- OUTCAR/OSZICAR completion and convergence evidence are inspected before any
  success claim.
- Warnings, force/stress thresholds, energy drift, and task-specific evidence
  are reviewed.

## Licensed POTCAR boundary

- POTCAR content is licensed material and must never be printed, quoted,
  committed, packaged, or stored as ordinary evidence.
- Resolve exact datasets in POSCAR order; never use wildcard fallback among
  variants such as `Fe`, `Fe_pv`, or `Fe_sv`.
- Only the SimFlow runtime may read and concatenate exact datasets from a
  user-owned POTCAR library into a controlled calculation directory. Fixed
  setup profiles may use `minimal`, `recommended`, or `gw` plus explicit
  element overrides.
- Do not return, print, snapshot, register as a normal artifact, commit,
  package, or redistribute POTCAR content.
- Guidance and returned evidence are metadata-only: element, exact dataset,
  ZVAL when available, size, SHA-256, and validation status.
- Any real transfer or execution involving POTCAR must be handed to runtime
  safety controls.

## Common failure modes

- Treating an unknown task as a static SCF calculation.
- Reusing incompatible WAVECAR/CHGCAR files.
- Declaring convergence from file existence or the last OSZICAR line alone.
- Applying bulk k-point or dipole assumptions to slabs, molecules, or defects.
- Silently changing pseudopotential variants or DFT+U conventions.
- Exposing POTCAR contents while trying to preserve provenance.

## Escalate uncertainty when

- The calculation class, magnetic state, charge state, reference energy, or
  pseudopotential dataset is ambiguous.
- Real execution, remote access, licensed files, or destructive cleanup is
  requested.
- Convergence or physical interpretation changes with a scientific parameter.

## Completion criteria

- VASP-specific inputs and outputs have been checked against the explicit task.
- Uncertainty and unsupported conclusions are visible.
- POTCAR handling remains exact, metadata-only, and non-redistributive.

## Optional references

Read only the references that materially match the request. For a concrete
calculation class, load the single matching `vasp_calc_*.md` reference. Combine
calculation-class references only when the workflow genuinely spans multiple
classes; do not load all of them unless the user requests a broad VASP audit.

- `references/vasp_official_sources.md`: Read when verifying exact VASP file,
  INCAR-tag, version-sensitive, or workflow semantics against official
  documentation.
- `references/vasp_parameters.md`: Read when reviewing common INCAR/KPOINTS
  choices, convergence policy, smearing, `NELECT`, `NBANDS`, `NCORE`/`NPAR`, or
  POTCAR metadata consistency.
- `references/vasp_task_checklists.md`: Read after classifying the request when
  a compact intake or cross-task review checklist is useful; pair it with the
  matching calculation-class reference for method-specific work.
- `references/vasp_troubleshooting.md`: Read when a run fails, converges poorly,
  emits warnings, produces suspicious output, or has restart or parsing
  problems.
- `references/vasp_tools.md`: Read when selecting or using py4vasp, VASPKIT, or
  another VASP-specific preparation or post-processing route.
- `references/vasp_calc_electronic_minimization.md`: Read for static SCF,
  fixed-structure ground states, charge-density generation, molecules, bulk
  systems, or electronic-minimization review.
- `references/vasp_calc_structure_optimization.md`: Read for ionic, cell, or
  volume relaxation, equation-of-state work, or Pulay-stress review.
- `references/vasp_calc_dos_band.md`: Read for total/projected DOS, DFT or hybrid
  band structures, k-paths, Fermi-level handling, and band/DOS figure
  provenance.
- `references/vasp_calc_magnetism_dftu_soc.md`: Read for spin-polarized states,
  magnetic-order comparisons, DFT+U, noncollinear magnetism, SOC, anisotropy, or
  spin spirals.
- `references/vasp_calc_aimd_mlff.md`: Read for AIMD, thermostat/barostat
  choices, constrained or enhanced MD, thermodynamic integration, or VASP MLFF
  training and deployment.
- `references/vasp_calc_neb_transition_states.md`: Read for NEB, climbing-image
  NEB, dimer, IRC, reaction paths, or transition-state searches.
- `references/vasp_calc_phonons_electron_phonon.md`: Read for finite-displacement
  or DFPT phonons, vibrations, phonon spectra, electron-phonon coupling, or
  phonon-related transport.
- `references/vasp_calc_surfaces_adsorption_stm.md`: Read for slabs, adsorption,
  work functions, dipole corrections, STM, or surface partial-charge analysis.
- `references/vasp_calc_defects_charged_systems.md`: Read for point defects,
  charged supercells, formation energies, potential alignment, electrostatic
  corrections, or defect spectroscopy.
- `references/vasp_calc_hybrid_meta_vdw.md`: Read for hybrid functionals,
  meta-GGA, nonlocal vdW, or empirical dispersion corrections.
- `references/vasp_calc_gw_rpa_bse.md`: Read for GW, RPA/ACFDT, BSE,
  quasiparticle, exciton, or related many-body workflows.
- `references/vasp_calc_optics_dielectric_eels.md`: Read for optical spectra,
  dielectric response, Born charges, piezoelectric response, Raman/IR setup, or
  EELS.
- `references/vasp_calc_xas_core_spectroscopy.md`: Read for XAS, supercell
  core-hole calculations, or BSE core excitations.
- `references/vasp_calc_nmr_efg_response.md`: Read for NMR shielding, EFG,
  hyperfine coupling, magnetic susceptibility, or related response properties.
- `references/vasp_calc_wannier_postprocessing.md`: Read for Wannierization,
  band interpolation, band-decomposed charges, py4vasp/VASPKIT workflows, or
  custom VASP post-processing.
