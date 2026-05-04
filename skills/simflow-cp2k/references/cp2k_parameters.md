# CP2K Key Parameters Reference

## Input File Structure

CP2K uses Fortran-namelist-style blocks: `&SECTION` / `&END SECTION`.

## GLOBAL Section

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| PROJECT | Job name (prefix for output files) | any string |
| RUN_TYPE | Calculation type | MD, ENERGY, GEO_OPT, CELL_OPT |
| PRINT_LEVEL | Output verbosity | LOW, MEDIUM, HIGH |

## FORCE_EVAL / DFT Section

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| BASIS_SET_FILE_NAME | Basis set library file | BASIS_MOLOPT, GTH_BASIS_SETS |
| POTENTIAL_FILE_NAME | Pseudopotential library | POTENTIAL |
| CHARGE | Total system charge | 0 (neutral) |
| MULTIPLICITY | Spin multiplicity | 1 (closed shell) |

## QS (Quickstep) Section

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| EPS_DEFAULT | Quickstep precision | 1.0E-6 to 1.0E-14 |
| EXTRAPOLATION | Wavefunction extrapolation | ASPC, LINEAR, NONE |
| EXTRAPOLATION_ORDER | Extrapolation order | 1-4 |

## MGRID (Multi-grid) Section

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| CUTOFF | Plane-wave cutoff (Ry) | 300-600 |
| REL_CUTOFF | Relative cutoff (Ry) | 40-80 |

## SCF Section

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| MAX_SCF | Max SCF iterations | 20-100 |
| EPS_SCF | SCF convergence threshold | 1.0E-5 to 1.0E-8 |
| SCF_GUESS | Initial guess | ATOMIC, RESTART |

## OT (Orbital Transformation) Section

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| MINIMIZER | OT minimizer | DIIS, CG, BROYDEN |
| PRECONDITIONER | Preconditioner | FULL_SINGLE_INVERSE, FULL_KINETIC |

## XC Section

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| XC_FUNCTIONAL | Exchange-correlation functional | PBE, PADE, BLYP, TPSS |

## MOTION/MD Section

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| ENSEMBLE | MD ensemble | NVT, NVE, NPT, NPH_I |
| STEPS | Number of MD steps | 100-100000 |
| TIMESTEP | Time step (fs) | 0.5-2.0 |
| TEMPERATURE | Target temperature (K) | 100-2000 |

## THERMOSTAT Section

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| TYPE | Thermostat type | CSVR, NOSE |
| TIMECON | Thermostat time constant (fs) | 50-500 |

## Basis Sets for H and O (DFT)

| Element | Basis Set | Potential |
|---------|-----------|-----------|
| H | DZVP-MOLOPT-SR-GTH | GTH-PBE-q1 |
| O | DZVP-MOLOPT-SR-GTH | GTH-PBE-q6 |
| H (TZ) | TZV2P-GTH | GTH-PBE-q1 |
| O (TZ) | TZV2P-GTH | GTH-PBE-q6 |

## Output Files

| File | Content |
|------|---------|
| `<project>.log` | Main output (energy, convergence, warnings) |
| `<project>-1.ener` | Per-step energy: step, time, kinetic, temp, potential, cons_qty, used_time |
| `<project>-pos-1.xyz` | MD trajectory (extended XYZ) |
| `<project>-1.restart` | Restart file for continuation |
| `<project>-vel-1.xyz` | Velocity trajectory |

## Convergence Indicators

- Normal end: `PROGRAM ENDED AT` in .log
- SCF converged: `SCF run converged` in .log
- Error: `ABORT` / `SEGMENTATION FAULT` in .log
