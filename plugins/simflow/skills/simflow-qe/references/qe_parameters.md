# Quantum ESPRESSO Key Parameters Reference

## pw.x Essential Parameters

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| calculation | Calculation type | scf, relax, vc-relax, md |
| ecutwfc | Kinetic energy cutoff (Ry) | 30-80 |
| ecutrho | Charge density cutoff (Ry) | 240-480 |
| conv_thr | SCF convergence (Ry) | 1E-8 to 1E-12 |
| etot_conv_thr | Total energy convergence (Ry) | 1E-4 to 1E-6 |
| forc_conv_thr | Force convergence (Ry/au) | 1E-3 to 1E-5 |
| K_POINTS | k-point mesh | 4x4x4 to 12x12x12 |
| pseudo_dir | Pseudopotential directory | System-dependent |

## Common Calculation Types

### Static SCF
```
&CONTROL
  calculation = 'scf'
  pseudo_dir = './pseudo/'
/
&SYSTEM
  ecutwfc = 50.0
  ecutrho = 400.0
/
&ELECTRONS
  conv_thr = 1D-10
/
```

### Geometry Relaxation
```
&CONTROL
  calculation = 'relax'
/
&IONS
  ion_dynamics = 'bfgs'
/
```

## Convergence Criteria

- SCF: conv_thr < 1E-8 Ry
- Ionic: etot_conv_thr < 1E-4 Ry
- Forces: < 1E-3 Ry/au
