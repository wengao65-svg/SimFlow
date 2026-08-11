---
name: simflow-vasp
description: Provide VASP-specific guidance for inputs, validation, convergence, troubleshooting, output interpretation, and licensed POTCAR handling.
---

# VASP Domain Skill

## Purpose

Act as the VASP Domain Assistant for one current Research Task Skill. This Skill does
not own workflow progression, submission, approval, or SimFlow state.

## Use when

- The task involves INCAR, POSCAR, KPOINTS, POTCAR metadata, OUTCAR, OSZICAR,
  vasprun.xml, vaspout.h5, CHGCAR, WAVECAR, DOSCAR, EIGENVAL, or VASP errors.
- VASP-specific choices affect setup, convergence, parsing, or interpretation.

## Do not use when

- The task is engine-independent and does not require VASP semantics.
- Another Domain Skill more directly matches the actual software.

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

- `references/vasp_official_sources.md`
- `references/vasp_parameters.md`
- `references/vasp_task_checklists.md`
- `references/vasp_troubleshooting.md`
- `references/vasp_tools.md`
- `references/vasp_calc_electronic_minimization.md`
- `references/vasp_calc_structure_optimization.md`
- `references/vasp_calc_dos_band.md`
- `references/vasp_calc_magnetism_dftu_soc.md`
- `references/vasp_calc_aimd_mlff.md`
- `references/vasp_calc_neb_transition_states.md`
- `references/vasp_calc_phonons_electron_phonon.md`
- `references/vasp_calc_surfaces_adsorption_stm.md`
- `references/vasp_calc_defects_charged_systems.md`
- `references/vasp_calc_hybrid_meta_vdw.md`
- `references/vasp_calc_gw_rpa_bse.md`
- `references/vasp_calc_optics_dielectric_eels.md`
- `references/vasp_calc_xas_core_spectroscopy.md`
- `references/vasp_calc_nmr_efg_response.md`
- `references/vasp_calc_wannier_postprocessing.md`
