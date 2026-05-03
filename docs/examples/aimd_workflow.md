# AIMD Workflow Example

## Ab Initio Molecular Dynamics for Liquid Water

This example runs AIMD for a small water box at 300K.

### Step 1: Build Water Box

```bash
# Build from XYZ file
simflow-modeling build_structure --from-file water_64.xyz

# Or use ASE to build
python -c "
from ase.build import molecule
from ase import Atoms
import numpy as np

# Create 64 water molecules in a box
atoms = []
for i in range(4):
    for j in range(4):
        for k in range(4):
            w = molecule('H2O')
            w.translate([i*3.5, j*3.5, k*3.5])
            atoms.append(w)
box = Atoms(atoms)
box.set_cell([14, 14, 14])
box.set_pbc(True)
box.write('water_64.xyz')
"
```

### Step 2: Initialize AIMD Workflow

```bash
simflow-aimd init --structure water_64.cif
```

### Step 3: Generate AIMD Inputs

```bash
simflow-aimd generate_inputs \
  --code vasp \
  --structure water_64.cif \
  --temp 300 \
  --timestep 1 \
  --ensemble nvt \
  --steps 10000 \
  --thermostat langevin
```

Generates:
- `INCAR.aimd` — AIMD parameters (MDALGO, TEBEG, POTIM, NSW)
- `KPOINTS.gamma` — Gamma-only k-points (molecules)
- `POSCAR` — Structure
- `POTCAR` — Pseudopotentials

### Step 4: Submit

```bash
simflow hpc submit --script-path job.sh --scheduler slurm
```

AIMD is computationally expensive. Typical settings:
- 2-8 nodes, 16-32 tasks per node
- Walltime: 24-72 hours
- Use gamma-only for molecules

### Step 5: Monitor Trajectory

```bash
# Check job status
simflow hpc status --job-id 12345

# During run, check XDATCAR growth
wc -l XDATCAR
```

### Step 6: Analyze Trajectory

After completion:

```bash
simflow-aimd analyze \
  --trajectory XDATCAR \
  --topology POSCAR \
  --rdf --msd --energy
```

### Analysis Outputs

**RDF (Radial Distribution Function)**:
- O-O, O-H, H-H pair correlations
- First peak position indicates hydrogen bonding distance
- Integration gives coordination number

**MSD (Mean Square Displacement)**:
- Slope gives diffusion coefficient
- D = MSD / (6 * t) for 3D systems
- Water at 300K: D ≈ 2.3 × 10⁻⁵ cm²/s

**Energy Evolution**:
- Total energy should be conserved (NVE) or fluctuate around target (NVT)
- Temperature should equilibrate around target

### Step 7: Check Equilibration

```bash
simflow-aimd check_equilibration \
  --trajectory XDATCAR \
  --property temperature \
  --skip 1000
```

Checks that temperature has equilibrated after initial transient.

## Expected Outputs

```
.simflow/
├── artifacts/
│   ├── initial_structure.cif
│   ├── trajectory.xtc
│   ├── rdf_oxygen.png
│   ├── msd.png
│   ├── energy_evolution.png
│   ├── diffusion_coefficient.json
│   └── rdf_data.csv
└── state/
    └── workflow.json  # status: "completed"
```

## Tips

- Start with a small system (64 molecules) for testing
- Use NVT first to equilibrate, then switch to NVE for production
- Check energy conservation: ΔE/E < 10⁻⁴ per step
- Run at least 10ps after equilibration for reliable statistics
