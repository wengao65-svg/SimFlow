# VASP Task Checklists

Use this reference after classifying the VASP request. The checklists are evidence prompts, not fixed workflows. Unknown tasks should return candidates and missing information.

## Common intake

- Identify the research intent: preparation, validation, dry-run planning, troubleshooting, analysis, visualization, writing, or handoff.
- Record the stage: usually `modeling`, `computation`, or `analysis_visualization`.
- List available files and predecessor evidence.
- Record VASP version/executable family if known (`vasp_std`, `vasp_gam`, `vasp_ncl`).
- Check whether real execution is requested. If yes, require dry-run evidence and the approval gate before submitting anything.

## Static SCF

- Required evidence: `POSCAR`, `INCAR`, `KPOINTS`, licensed local `POTCAR` metadata.
- Check `NSW=0` or equivalent static intent.
- Check `ENCUT`, k-point density, smearing, `EDIFF`, `ISPIN/MAGMOM`, and any restart choices.
- Record whether `CHGCAR` and `WAVECAR` outputs are needed for downstream DOS/band/SOC/hybrid work.
- Do not infer convergence from file existence alone; inspect `OUTCAR`, `OSZICAR`, `vasprun.xml`, or `vaspout.h5`.

## Geometry relaxation

- Required evidence: static-style input set plus relaxation intent.
- Check `IBRION`, `NSW`, `ISIF`, `EDIFFG`, `POTIM`, constraints/selective dynamics, and whether cell relaxation is scientifically intended.
- Verify final forces/stress and whether `CONTCAR` is usable as a new structure.
- Do not silently compare unrelaxed and relaxed total energies as equivalent evidence.

## DOS and band structure

- Required predecessors: converged static SCF and compatible `CHGCAR`; `WAVECAR` when the chosen workflow needs it.
- DOS: check dense k mesh, `ICHARG`, `ISMEAR/SIGMA`, `LORBIT`, `NEDOS`, projected-DOS choices, and spin/SOC consistency.
- Band: check line-mode `KPOINTS`, high-symmetry labels/path provenance, `ICHARG`, and Fermi-level source.
- Record whether plotted bands use `EIGENVAL`, `vasprun.xml`, py4vasp, VASPKIT, or a custom parser.
- For metals, explain smearing/Fermi-level handling and avoid over-interpreting band gaps.

## AIMD

- Required evidence: equilibrated structure, ensemble choice, temperature schedule, timestep, run length, thermostat/barostat parameters, and output cadence.
- Check `IBRION=0`, `NSW>0`, `POTIM`, `TEBEG/TEEND`, `MDALGO` or legacy thermostat tags, `ISIF`, and restart policy.
- Separate equilibration and production evidence.
- For transport/statistics, record trajectory length, sampling interval, discarded transient, time origins, uncertainty estimate, and unit conversion.
- Real AIMD execution is high-cost compute and requires the approval gate.

## NEB and transition states

- Required evidence: converged initial/final states, image directories, consistent atom count/order, shared `POTCAR` metadata, and `KPOINTS`.
- Check `IMAGES`, `IBRION`, `POTIM`, spring/climbing-image choices, endpoint constraints, and whether images were interpolated sensibly.
- Verify each image's `POSCAR/CONTCAR` order and avoid changing species order.
- Do not record a transition state as found until convergence and highest-energy image evidence are inspected.

## Phonons and vibrations

- Classify finite-displacement, DFPT, molecular vibration, or external-tool workflow.
- Required evidence: well-converged relaxed structure, supercell/displacement plan or DFPT tags, force convergence target, and non-analytical correction intent if relevant.
- Record external tool provenance when using phonopy, py4vasp, pymatgen, ASE, or custom scripts.
- Do not infer thermodynamic or dynamical stability from incomplete displacement sets.

## Surface, adsorption, and defects

- Surface: record slab source, Miller index, termination, vacuum, dipole correction need, k mesh, relaxed layers, and reference bulk.
- Adsorption: record adsorbate geometry, sites tested, coverage, charge/spin, reference energies, and whether dispersion corrections are used.
- Defects: record pristine reference, supercell size, charge state, chemical potentials, correction scheme, potential alignment, and finite-size risks.
- Never overwrite user structures; write generated variants under a clearly named output directory.

## Magnetism, DFT+U, SOC, and noncollinear calculations

- Magnetism: record initial `MAGMOM`, target magnetic states, `ISPIN`, symmetry decisions, and whether multiple initial states were tested.
- DFT+U: record element, orbital (`LDAUL`), U/J values (`LDAUU/LDAUJ`), literature/provenance, and sensitivity plan.
- SOC/noncollinear: record scalar-relativistic predecessor, `vasp_ncl` need, `LSORBIT`, `LNONCOLLINEAR`, `SAXIS`, `MAGMOM`, symmetry decisions, and spin quantization assumptions.
- Do not mix SOC/non-SOC, different U values, or different pseudopotential families in scientific comparisons without explicit rationale.

## Hybrid, GW, BSE, RPA, and optics

- Treat these as high-cost advanced methods that require stronger convergence and resource review.
- Hybrid: check `LHFCALC`, `HFSCREEN`, `AEXX`, `ALGO`, k mesh, restart strategy, and compatibility with preceding density/orbitals.
- GW/RPA/BSE: require empty-band, cutoff, frequency/grid, and predecessor workflow evidence; NBANDS convergence is mandatory.
- Optics/dielectric: check `LOPTICS`, `LEPSILON`, `NBANDS`, `WAVEDER`, smearing, local-field choices, and tensor interpretation.
- Do not present single-parameter advanced-method output as converged unless the convergence evidence is present.

## Output and handoff review

- Parse convergence from actual outputs, not just process completion.
- Record warnings/errors, final energy, force/stress criteria, number of electronic/ionic steps, elapsed/resource estimates, and output file lineage.
- For figures, record input file, parser/tool, plot script, Fermi-energy source, axis choices, and post-processing parameters.
- Handoff should include produced artifacts, latest checkpoint, unresolved risks, missing inputs, and whether approval is needed for real execution.
