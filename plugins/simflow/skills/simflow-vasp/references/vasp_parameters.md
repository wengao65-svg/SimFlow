# VASP Parameter Reference

Use this reference for parameter policy and risk reminders. Verify task-specific details against official VASP documentation when the choice affects a scientific result.

## Official parameter sources

- INCAR overview: https://www.vasp.at/wiki/INCAR
- INCAR tag category: https://www.vasp.at/wiki/Category:INCAR_tag
- KPOINTS: https://www.vasp.at/wiki/KPOINTS
- POSCAR: https://www.vasp.at/wiki/POSCAR
- POTCAR: https://www.vasp.at/wiki/POTCAR
- NBANDS: https://www.vasp.at/wiki/NBANDS
- NELECT: https://www.vasp.at/wiki/NELECT
- Smearing: https://www.vasp.at/wiki/Smearing_technique
- NCORE: https://www.vasp.at/wiki/NCORE
- NPAR: https://www.vasp.at/wiki/NPAR
- Optimizing parallelization: https://www.vasp.at/wiki/Optimizing_the_parallelization
- GPU ports of VASP: https://www.vasp.at/wiki/GPU_ports_of_VASP

## INCAR essential parameters

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| ENCUT | Plane-wave cutoff energy (eV) | 400-600 |
| EDIFF | SCF convergence criteria | 1E-5 to 1E-8 |
| EDIFFG | Ionic convergence criteria (eV/A) | -0.01 to -0.05 |
| NSW | Maximum ionic steps | 0 (static), 50-200 (relax) |
| IBRION | Ionic relaxation algorithm | 1 (RMM-D), 2 (CG) |
| ISIF | Stress/atom relaxation | 2 (atoms), 3 (atoms+cell) |
| ISPIN | Spin polarization | 1 (non-mag), 2 (mag) |
| MAGMOM | Initial magnetic moments | Element-dependent |
| KPOINTS | k-point mesh | 4x4x4 to 12x12x12 |
| POTCAR | Pseudopotential | PAW recommended |

Treat these ranges as prompts for review, not universal defaults. Values should be tied to pseudopotentials, structure size, target property, and convergence evidence.

## Common calculation motifs

### Static SCF

```
NSW = 0
ISMEAR = 0
SIGMA = 0.05
```

### Geometry Optimization

```
NSW = 100
IBRION = 2
ISIF = 3
EDIFFG = -0.02
```

### DOS Calculation

```
NSW = 0
ISMEAR = -5
LORBIT = 11
NEDOS = 3001
```

## Convergence criteria

- SCF: EDIFF < 1E-6
- Ionic: |forces| < 0.01 eV/A
- Energy change: < 1E-5 eV between ionic steps

These are common research-grade targets, not automatic pass/fail standards. Record the user's intended accuracy and the property being computed.

## Smearing policy reminders

- Metals usually need finite smearing and careful Fermi-level interpretation.
- Insulators/semiconductors often use small smearing or tetrahedron-style approaches for final static/DOS work, depending on the task.
- Do not reuse a smearing setting blindly across relax, static, DOS, band, and optical workflows.
- Record `ISMEAR`, `SIGMA`, and whether total energies are being compared across compatible settings.

## KPOINTS policy reminders

- Mesh k-points are normally used for relax/static/DOS/AIMD.
- Line-mode k-points are normally used for band structures after a converged charge-density predecessor.
- Gamma-centered meshes are often used for large supercells, surfaces, defects, and molecules; Monkhorst-Pack may be appropriate for bulk systems.
- K-point convergence evidence should be recorded for quantitative energies, forces, barriers, and formation energies.

## POTCAR and NELECT discipline

- SimFlow must not generate, copy, distribute, snapshot, or print POTCAR content.
- Record metadata only: element order, pseudopotential family/flavor/date labels, ZVAL-derived `NELECT` when locally available, and hashes/provenance when allowed.
- POSCAR species order and POTCAR block order must match.
- Do not mix pseudopotential families or variants in comparative studies without explicit rationale.

## NBANDS Policy

NBANDS controls the number of electronic bands in VASP. The default behavior
is to let VASP auto-determine NBANDS, which is safe for ordinary calculations.

### NELECT: Valence Electrons (not atomic number total)

Critical: NELECT in VASP is the total number of valence electrons from
POTCAR ZVAL, NOT the sum of atomic numbers. For example, Si 8-atom cell:
- Atomic number total = 14 × 8 = 112 (wrong for NELECT)
- POTCAR ZVAL for Si = 4
- NELECT = 4 × 8 = 32 (correct)
- occupied_bands = 32 / 2 = 16

NELECT must be read from POTCAR (`POMASS = ...; ZVAL = ...` lines) or
explicitly provided by the user.

### Default Behavior: No NBANDS

For ordinary calculations, do **not** write NBANDS in INCAR:
- `relax`, `scf`, `static`, `bands`, `dos`, `nscf`

VASP's default formula (approximation):
```
NBANDS = max(
    nint((NELECT + 2) / 2) + max(NIONS / 2, 3),
    0.6 * NELECT
)
```
For noncollinear calculations, multiply by 2.

This default already includes empty bands beyond the occupied states.

### User-Explicit NBANDS

If the user explicitly provides NBANDS, it must satisfy:
```
NBANDS > occupied_bands = ceil(NELECT / 2)
```
Otherwise, raise an error. For spin-polarized (ISPIN=2):
```
occupied_bands = ceil((NELECT + |MAGMOM|) / 2)
```

### Special Calculation Types

| Calculation Type    | NBANDS Multiplier | Notes |
|---------------------|-------------------|-------|
| optics / dielectric / eels | 2.5× VASP default | Optical transitions need empty bands |
| gw / rpa / bse / crpa     | 3.0× VASP default | Must do NBANDS convergence test |
| wannier / high_energy_window | 1.5× VASP default | Depends on outer energy window |

### Key VASP Wiki References

- **NBANDS**: Minimum = occupied + 1 (warning if too low). Default includes padding.
- **NELECT**: Total valence electrons, determined by POTCAR ZVAL × atom count.
- **LOPTICS**: Needs many empty bands. Recommended 2–3× default NBANDS.
- **GW**: Self-energy summation over empty states requires large NBANDS.
  Convergence test mandatory: increase NBANDS until quasiparticle energies converge.
- **WAVEDER**: Optical derivatives. NBANDS must be consistent with the generating step.

### Implementation

Core logic: `runtime/simflow_helpers/engines/vasp_incar.py`
- `choose_nbands()` — returns `None` (don't write) or `int` (write this value)
- `apply_nbands_policy()` — modifies INCAR dict in-place
- `get_explicit_user_nbands()` — distinguishes user value from template residual

## NCORE / NPAR Policy

`NCORE` and `NPAR` control band-level parallelization and are inverse choices
for a fixed number of available ranks. SimFlow should not auto-generate both at
the same time. If the user explicitly supplies both, preserve the values but
warn that benchmarking is needed and that `NPAR` takes precedence in VASP.

### Hardware-context rule

Do not guess the execution hardware from a structure or calculation type:
- Unknown hardware or missing submit-script evidence: omit both `NCORE` and
  `NPAR`, report missing execution context, and ask whether the target run is
  CPU-only or GPU/OpenACC/OpenMP-offload.
- Confirmed GPU/OpenACC/OpenMP-offload execution: omit both by default. VASP
  GPU/offload paths reset or avoid `NCORE > 1`; use GPU/OpenMP/KPAR/NSIM
  guidance from the official GPU and parallelization pages instead.
- Confirmed CPU execution with no user preference: write `NPAR = 4`.
- Confirmed CPU execution with user preference `parallel_preference=ncore`:
  write `NCORE` only when per-socket or per-NUMA-domain core evidence is known.
  Example: two CPUs with 128 total cores means `NCORE = 64` if the topology is
  two 64-core sockets and this is the intended CPU tuning.
- User-explicit `NCORE` or `NPAR`: preserve the explicit value and record the
  hardware-context warning if the target is accelerated or unknown.

### Evidence sources

Acceptable execution-context evidence includes explicit user parameters,
preserved submit scripts, resource-manager GPU directives, GPU/offload
environment variables, module/executable names that clearly indicate
OpenACC/GPU/offload builds, or approved remote inspection. Remote or HPC
inspection requires the normal SimFlow safety approval discipline; do not SSH
or probe a machine just to infer these tags without approval.

### Implementation

Core logic: `runtime/simflow_helpers/engines/vasp_incar.py`
- `infer_vasp_execution_context()` — conservatively classifies CPU,
  accelerated, or unknown execution evidence
- `apply_ncore_npar_policy()` — removes residual tags, preserves explicit user
  tags, and writes only the safe default for confirmed CPU mode
- `filter_vasp_incar_params()` — prevents SimFlow control keys such as
  execution context and submit-script paths from being written as INCAR tags

## Advanced-method parameter provenance

- DFT+U: record `LDAU`, `LDAUTYPE`, `LDAUL`, `LDAUU`, `LDAUJ`, target orbitals, literature/user provenance, and sensitivity plan.
- SOC/noncollinear: record `LSORBIT`, `LNONCOLLINEAR`, `SAXIS`, `MAGMOM`, executable family, symmetry choices, and scalar-relativistic predecessor.
- Hybrid: record `LHFCALC`, `HFSCREEN`, `AEXX`, `ALGO`, k mesh, restart strategy, and resource estimate.
- Optics/dielectric: record `LOPTICS`, `LEPSILON`, `NBANDS`, `NEDOS`, smearing, and tensor interpretation.
- AIMD: record `IBRION`, `NSW`, `POTIM`, `TEBEG`, `TEEND`, `MDALGO` or thermostat tags, ensemble, timestep, and output cadence.
