# VASP Key Parameters Reference

## INCAR Essential Parameters

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

## Common Calculation Types

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

## Convergence Criteria

- SCF: EDIFF < 1E-6
- Ionic: |forces| < 0.01 eV/A
- Energy change: < 1E-5 eV between ionic steps

## NBANDS Policy

NBANDS controls the number of electronic bands in VASP. The default behavior
is to let VASP auto-determine NBANDS, which is safe for ordinary calculations.

### NELECT: Valence Electrons (not atomic number total)

**Critical**: NELECT in VASP is the total number of **valence electrons** from
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

Core logic: `runtime/lib/vasp_incar.py`
- `choose_nbands()` — returns `None` (don't write) or `int` (write this value)
- `apply_nbands_policy()` — modifies INCAR dict in-place
- `get_explicit_user_nbands()` — distinguishes user value from template residual
