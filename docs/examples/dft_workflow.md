# DFT Workflow Example

## Complete Si Diamond DFT Calculation

This example walks through a full DFT workflow for silicon diamond structure.

### Step 1: Build Structure

```bash
# Build Si diamond unit cell
simflow-modeling build_structure --type diamond --element Si --lattice-const 5.43

# Creates: Si.cif
# Verify: simflow-modeling validate_structure --input Si.cif
```

### Step 2: Initialize Workflow

```bash
simflow-dft init --structure Si.cif --workflow dft
```

Creates `.simflow/` directory with workflow state.

### Step 3: Generate VASP Inputs

```bash
simflow-dft generate_inputs \
  --code vasp \
  --structure Si.cif \
  --functional PBE \
  --encut 520 \
  --kpoints-density 0.03
```

Generates:
- `INCAR.relax` — Relaxation parameters
- `KPOINTS.mesh` — k-point mesh
- `POSCAR` — Structure in VASP format
- `POTCAR` — Pseudopotential (requires VASP potpaw)

### Step 4: Dry Run

```bash
simflow hpc dry_run --script-path job.sh
```

Validates:
- Input files exist and are syntactically correct
- POTCAR species match POSCAR
- KPOINTS mesh is reasonable

### Step 5: Submit Relaxation

```bash
simflow hpc submit --script-path job.sh --scheduler slurm
# Returns: job_id = 12345
```

### Step 6: Monitor

```bash
simflow hpc status --job-id 12345 --scheduler slurm
```

### Step 7: Check Convergence

```bash
simflow-dft analyze --stage relax
```

Checks:
- Electronic convergence (EDIFF achieved)
- Ionic convergence (forces < EDIFFG)
- Energy change between ionic steps

### Step 8: Run SCF

After relaxation converges:

```bash
simflow-dft run_scf --structure relaxed_POSCAR --encut 520
```

### Step 9: Run Bands

```bash
simflow-dft run_bands --structure relaxed_POSCAR --kpath "L-G-X-W-K"
```

### Step 10: Run DOS

```bash
simflow-dft run_dos --structure relaxed_POSCAR --kpoints-density 0.01
```

### Step 11: Analysis

```bash
simflow-dft analyze --stage all
```

Generates:
- Band structure plot (PNG)
- DOS plot (PNG)
- Energy summary (JSON)
- Convergence report (JSON)

## Expected Outputs

```
.simflow/
├── artifacts/
│   ├── initial_structure.cif
│   ├── relaxed_structure.cif
│   ├── energy.dat
│   ├── band_structure.png
│   ├── dos.png
│   └── convergence_report.json
└── state/
    └── workflow.json  # status: "completed"
```

## Troubleshooting

- **SCF not converging**: Increase ENCUT, check POTCAR, try different mixing
- **Relaxation not converging**: Reduce EDIFFG, increase NSW, check initial forces
- **Band structure looks wrong**: Verify k-path, check symmetry analysis
