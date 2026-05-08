# Gaussian Key Parameters Reference

## Common Methods and Basis Sets

| Method | Description | Typical Use |
|--------|-------------|-------------|
| HF | Hartree-Fock | Reference method |
| B3LYP | Hybrid DFT | Organic molecules |
| PBE0 | Hybrid GGA | Solids/surfaces |
| MP2 | Post-HF | Correlation energy |
| CCSD(T) | Coupled cluster | Benchmark accuracy |

| Basis Set | Description | Typical Use |
|-----------|-------------|-------------|
| 6-31G* | Split valence + polarization | Organic molecules |
| 6-311++G** | Triple zeta + diffuse | Anions, excited states |
| def2-TZVP | Triple zeta | Transition metals |
| cc-pVDZ | Correlation consistent | High accuracy |

## Common Job Types

### Geometry Optimization
```
# B3LYP/6-31G* Opt

Title

0 1
C  0.0  0.0  0.0
H  0.0  0.0  1.09
...
```

### Frequency Calculation
```
# B3LYP/6-31G* Opt Freq

Title

0 1
...
```

### Single Point Energy
```
# B3LYP/6-311++G** SP

Title

0 1
...
```

## Convergence Criteria

- Optimization: Max Force < 0.00045, RMS Force < 0.0003
- SCF: Default (usually sufficient)
- Frequency: No imaginary frequencies for minima
