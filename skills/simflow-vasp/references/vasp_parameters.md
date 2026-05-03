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
