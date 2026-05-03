# MD Workflow Example

## Classical MD for Silicon with Stillinger-Weber Potential

This example runs classical MD for a Si supercell using the Stillinger-Weber potential.

### Step 1: Build Supercell

```bash
# Build 4x4x4 Si supercell (512 atoms)
simflow-modeling build_structure --type diamond --element Si --lattice-const 5.43
simflow-modeling make_supercell --input Si.cif --dims 4 4 4

# Creates: Si_4x4x4.cif
```

### Step 2: Initialize MD Workflow

```bash
simflow-md init --structure Si_4x4x4.cif
```

### Step 3: Generate LAMMPS Inputs

```bash
simflow-md generate_inputs \
  --code lammps \
  --structure Si_4x4x4.cif \
  --forcefield StillingerWeber \
  --ensemble npt \
  --temp 300 \
  --pressure 1.0 \
  --timestep 0.001 \
  --steps 100000
```

Generates:
- `Si.sw` — Stillinger-Weber potential file
- `in.equilibration` — LAMMPS input script
- `Si.data` — LAMMPS data file

### Step 4: Equilibration

```bash
simflow-md run_equilibrate \
  --input in.equilibration \
  --ensemble npt \
  --temp 300 \
  --pressure 1.0 \
  --steps 50000
```

NPT equilibration allows box to adjust to target pressure.

### Step 5: Production Run

```bash
simflow-md run_production \
  --input in.production \
  --ensemble nve \
  --steps 50000 \
  --dump-frequency 100
```

Production run at constant energy for transport properties.

### Step 6: Analyze

```bash
simflow-md analyze \
  --trajectory dump.lammps \
  --topology Si.data \
  --rdf --msd --thermodynamics
```

### Analysis Outputs

**RDF**:
- Si-Si pair correlation
- First peak at ~2.35 Å (Si-Si bond length in diamond structure)
- Second peak at ~3.84 Å

**MSD**:
- Crystalline Si: MSD should plateau (no diffusion)
- Liquid Si: MSD slope gives diffusion coefficient

**Thermodynamics**:
- Temperature evolution
- Pressure evolution
- Potential/kinetic energy decomposition

## LAMMPS Input Script Template

```lammps
# Si Stillinger-Weber MD
units           metal
atom_style      atomic
boundary        p p p

read_data       Si.data
pair_style      sw
pair_coeff      * * Si.sw Si

# Equilibration (NPT)
fix             1 all npt temp 300 300 0.1 iso 1.0 1.0 1.0
timestep        0.001
thermo          100
thermo_style    custom step temp press pe ke etotal

# Dump trajectory
dump            1 all custom 100 dump.lammps id type x y z vx vy vz

# Run equilibration
run             50000

# Production (NVE)
unfix           1
fix             2 all nve
run             50000
```

## Expected Outputs

```
.simflow/
├── artifacts/
│   ├── Si_4x4x4.cif
│   ├── dump.lammps
│   ├── rdf_si.png
│   ├── msd.png
│   ├── thermodynamics.png
│   └── analysis_summary.json
└── state/
    └── workflow.json  # status: "completed"
```

## Force Fields

| Potential | Material | Description |
|-----------|----------|-------------|
| Stillinger-Weber | Si, Ge | Tetrahedral bonding |
| EAM | Metals (Cu, Al, Fe) | Embedded atom method |
| LJ | Noble gases, simple liquids | Lennard-Jones |
| TIP4P | Water | Rigid water models |
| CHARMM | Biomolecules | Biomolecular force field |
