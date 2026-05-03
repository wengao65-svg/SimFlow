# Software Skills Reference

## VASP Skills

### generate_vasp_inputs

Generate VASP input files (INCAR, KPOINTS, POSCAR, POTCAR).

```bash
simflow-dft generate_inputs \
  --code vasp \
  --structure Si.cif \
  --functional PBE \
  --encut 520 \
  --kpoints-density 0.03
```

### run_relax

Structural relaxation with VASP.

```bash
simflow-dft run_relax \
  --structure POSCAR \
  --encut 520 \
  --ediff 1e-6 \
  --ibrion 2 \
  --nsw 100
```

### run_scf

Single-point energy calculation.

### run_bands

Band structure calculation along high-symmetry paths.

### run_dos

Density of states calculation.

## Quantum ESPRESSO Skills

### generate_qe_inputs

Generate QE input files (pw.in).

```bash
simflow-dft generate_inputs \
  --code qe \
  --structure Si.cif \
  --ecutwfc 60 \
  --ecutrho 480
```

### run_relax_qe

Structural relaxation with QE.

## LAMMPS Skills

### generate_lammps_inputs

Generate LAMMPS input scripts.

```bash
simflow-md generate_inputs \
  --code lammps \
  --structure Si.data \
  --forcefield StillingerWeber \
  --ensemble npt \
  --temp 300 \
  --pressure 1.0
```

### run_equilibrate

NVT/NPT equilibration.

### run_production

Production MD run.

## Analysis Skills

### analyze_md_trajectory

MD trajectory analysis with MDAnalysis.

```bash
simflow-aimd analyze \
  --trajectory XDATCAR \
  --topology POSCAR \
  --rdf --msd --energy
```

Outputs:
- RDF plot (PNG)
- MSD plot (PNG)
- Energy evolution (PNG)
- Numerical data (CSV)

### plot_energy_curve

Energy vs. volume or parameter sweep plot.

### validate_structure

Structure validation checks:
- Lattice parameter sanity
- Bond length checks
- Atomic overlap detection
