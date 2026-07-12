---
name: simflow-vasp
description: Provide VASP domain assistance for official-documentation lookup, input preparation, validation, dry-run planning, troubleshooting, output parsing, analysis/visualization, and artifact recording. Use when Codex works with VASP, INCAR, POSCAR, POTCAR metadata, KPOINTS, OUTCAR, OSZICAR, vasprun.xml, vaspout.h5, CHGCAR, WAVECAR, DOSCAR, EIGENVAL, NEB, phonons, AIMD, SOC, hybrid functionals, DFT+U, GW/BSE/RPA, defects, surfaces, adsorption, py4vasp, VASPKIT, or VASP-related SimFlow handoff.
---

# SimFlow VASP

`simflow-vasp` is a domain assistant. It helps the host agent use VASP official documentation, local evidence, SimFlow state, optional helper scripts, and conservative scientific checks. It is not a central workflow executor and does not define the full VASP capability surface.

## Trigger conditions

- User mentions VASP, INCAR, POSCAR, POTCAR metadata, KPOINTS, OUTCAR, OSZICAR, vasprun.xml, vaspout.h5, CHGCAR, WAVECAR, DOSCAR, EIGENVAL, NEB, phonons, AIMD, SOC, hybrid functionals, DFT+U, GW/BSE/RPA, defects, surfaces, or adsorption.
- A computation, modeling, analysis, visualization, troubleshooting, or writing task needs VASP-specific context.
- User asks to inspect, prepare, validate, troubleshoot, parse, analyze, visualize, or hand off VASP-related artifacts.

## Input conditions

- Natural-language VASP intent, local files, artifact ids, calculation directory, or previous checkpoint.
- Optional user-selected task type, software version, script, parser, template, or external tool.
- Unknown or unlisted tasks should return candidates and missing information, not a forced alias such as `static`.
- For ambiguous setup, clarify at least calculation intent, available predecessors, structure/source files, spin/charge/SOC/DFT+U/hybrid choices, intended accuracy, and whether any real execution is requested.

## Output artifacts

- Optional official-source note, input manifest, validation report, dry-run/compute-plan note, analysis/troubleshooting report, figure/caption, reproducibility note, or handoff note.
- Optional helper-run manifest when using SimFlow parsers, py4vasp, VASPKIT, custom Python, shell commands, or user scripts.
- Artifact metadata should record source files, command/tool choice, parameters, assumptions, task uncertainty, environment, hashes when available, and lineage.

## Status write rules

- Resolve explicit `project_root` before writing `.simflow/` state, artifacts, checkpoints, reports, or lineage.
- Write reports only as evidence records; do not advance a fixed VASP workflow automatically.
- Helper outputs are pure evidence producers by default. They may write
  requested VASP inputs or reports under `project_root`, but they do not
  initialize or advance stages, do not register artifacts, and do not create
  checkpoints unless explicit helper-run recording is requested.
- Default helper report paths live under project-root `reports/<engine>/`.
  `.simflow` is touched only by explicit helper-run recording.
- `--record-helper-run` is `record_only`: it records helper evidence and
  lineage only. Canonical stage runners own stage transitions, and
  checkpoint/state-admin APIs own checkpoint operations.
- Direct helpers do not register arbitrary report artifacts. Canonical stage
  runners may ingest/register outputs when the workflow stage owns them.
- Use open stages such as `modeling`, `computation`, or `analysis_visualization` according to research intent.
- Keep recipe/tag values such as `dft`, `aimd`, `neb`, `phonon`, `defect`, or `custom` separate from workflow stage.
- Do not write under `.omx/`; it belongs to the host session, not SimFlow workflow state.

## Working procedure

1. Read `.simflow/state/` before acting and resolve `project_root` explicitly before any SimFlow write.
2. Classify the request as preparation, validation, dry-run planning, troubleshooting, parsing, analysis/visualization, writing, or handoff. Return uncertainty when the task does not match a known safe pattern.
3. Prefer official VASP sources for parameter or workflow claims. Load `references/vasp_official_sources.md` for documentation navigation, `references/vasp_task_checklists.md` for task-specific checks, `references/vasp_parameters.md` for parameter policies, and `references/vasp_troubleshooting.md` for convergence/error diagnosis.
4. For a concrete calculation class, load only the matching `references/vasp_calc_*.md` file listed below. Avoid loading all calculation references unless the user asks for a broad VASP workflow audit.
5. Inspect local inputs before generating or interpreting results. Preserve user-provided files and report missing predecessors instead of inventing them.
6. Default compute work to dry-run/static inspection. Real local, remote, or HPC execution requires the same approval gate evidence used by `simflow-computation`.
7. Register outputs as artifacts with metadata and lineage only when explicit helper-run recording is requested or when a canonical stage runner ingests those outputs.

## Calculation-class references

- `references/vasp_calc_electronic_minimization.md`: SCF/static electronic minimization, molecules, bulk ground states, and dry-run setup review.
- `references/vasp_calc_structure_optimization.md`: ionic/cell relaxation, equation-of-state, volume relaxation, Pulay-stress review.
- `references/vasp_calc_dos_band.md`: DOS, projected DOS, DFT band structures, hybrid band structures, Fermi-level handling.
- `references/vasp_calc_magnetism_dftu_soc.md`: collinear magnetism, DFT+U, noncollinear magnetism, SOC, spin spirals.
- `references/vasp_calc_aimd_mlff.md`: ab-initio MD, thermostats, enhanced/constrained MD, thermodynamic integration, MLFF training/application.
- `references/vasp_calc_neb_transition_states.md`: NEB, dimer, IRC, static/dynamic transition-state workflows.
- `references/vasp_calc_phonons_electron_phonon.md`: finite-displacement phonons, DFPT phonons, phonon DOS/dispersion, electron-phonon calculations.
- `references/vasp_calc_surfaces_adsorption_stm.md`: slabs, adsorption, work functions, dipole corrections, partial charge density, STM.
- `references/vasp_calc_defects_charged_systems.md`: point defects, charged cells, electrostatic corrections, potential alignment.
- `references/vasp_calc_hybrid_meta_vdw.md`: hybrid functionals, meta-GGA, van der Waals and dispersion corrections.
- `references/vasp_calc_gw_rpa_bse.md`: GW, RPA/ACFDT, BSE, quasiparticles, excitons.
- `references/vasp_calc_optics_dielectric_eels.md`: optical spectra, static dielectric response, Born charges, EELS.
- `references/vasp_calc_xas_core_spectroscopy.md`: XAS, supercell core-hole, BSE core excitations.
- `references/vasp_calc_nmr_efg_response.md`: NMR shielding, electric-field gradients, hyperfine coupling, response calculations.
- `references/vasp_calc_wannier_postprocessing.md`: Wannier orbitals, partial/band-decomposed charges, py4vasp/VASPKIT/custom post-processing.

## Recommended checks

- Input set: `POSCAR`, `INCAR`, `KPOINTS`, and licensed local `POTCAR` metadata are present and mutually consistent for the requested task.
- Structure: POSCAR species/counts, lattice, selective dynamics, surface vacuum, defect supercell, adsorption geometry, and charge/spin assumptions are explicit.
- POTCAR: element order and ZVAL evidence are checked without copying, printing, snapshotting, or distributing POTCAR content.
- KPOINTS: mesh density, Gamma/Monkhorst choice, line-mode paths for bands, and finite-size/k-point convergence are appropriate for the system.
- INCAR: task labels match `NSW`, `IBRION`, `ISIF`, `ISMEAR`, `SIGMA`, `EDIFF`, `EDIFFG`, `ISPIN`, `MAGMOM`, `LREAL`, `LASPH`, and any advanced tags.
- Predecessors: DOS/band workflows have a prior static SCF charge density; NEB has endpoint/images; phonons have a displacement or DFPT plan; restart/continuation has compatible `WAVECAR`/`CHGCAR`/`CONTCAR` evidence.
- Advanced methods: DFT+U, SOC, noncollinear magnetism, hybrid functionals, GW/BSE/RPA, optics, AIMD, defects, surfaces, and adsorption include method-specific provenance and convergence risks.
- Outputs: convergence, warnings, final structure, forces/stress, energies, k-point path, Fermi level, occupations, and figure lineage are traceable to inputs and commands.
- Reproducibility: VASP version, executable family, pseudopotential flavor/date metadata, relevant environment/module information, helper versions, and source URLs are recorded when available.

## Optional helper scripts

- `scripts/generate_vasp_inputs.py`: Generate a conservative VASP input set from a structure using pymatgen. It writes POTCAR metadata/instructions only; it does not generate or distribute POTCAR content.
- `scripts/orchestrate_vasp_task.py`: Build SimFlow VASP reports, dry-run plans, and helper-run evidence for common tasks without submitting jobs.
- `scripts/validate_vasp_outputs.py`: Inspect VASP outputs for convergence and obvious warning/error evidence.
- `scripts/troubleshoot_vasp.py`: Produce source-backed troubleshooting notes using official VASP/py4vasp documentation links.
- `scripts/plot_band_structure.py`: Plot a band structure from `EIGENVAL` and optional line-mode `KPOINTS`, recording helper-run metadata when requested.

These helpers are optional domain tools, not the only valid parser, builder, analysis path, or report format. User scripts, py4vasp, VASPKIT, pymatgen, ASE, notebooks, shell commands, or custom Python are acceptable when evidence, lineage, assumptions, and risks are recorded.

## Checkpoint rules

- VASP helpers do not create stage-boundary checkpoints by default.
- Helper-run recording remains `record_only`; use canonical stage runners or
  checkpoint/state-admin APIs when checkpoint operations are explicitly needed.

## Prohibited actions

- Do not default unknown VASP tasks to `static`.
- Do not treat common aliases as the full VASP capability surface.
- Do not require py4vasp, VASPKIT, SimFlow parsers, fixed report names, or generated templates as the only valid path.
- Do not generate, concatenate, copy, move, print, snapshot, or invoke VASPKIT
  to produce POTCAR content.
- Do not fabricate VASP results, literature, figures, citations, convergence status, or completed calculations.
- Do not record unfinished or failed calculations as completed results.
- Do not submit real local, remote, or HPC jobs from this skill without the relevant approval gate.

## Manual confirmation scenarios

- Task intent, predecessors, charge/spin/SOC/DFT+U/hybrid/phonon/NEB setup, or validation standard is ambiguous.
- Real execution, licensed files, proprietary files, credentials, remote systems, or high-cost resources are involved.
- Existing user inputs would be overwritten or interpreted in a way that changes scientific meaning.
- The requested analysis method would materially affect a scientific conclusion, figure, or manuscript claim.
