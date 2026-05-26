# LAMMPS Safe Dry-Run Example

This example creates a redistributable LAMMPS evidence package without running
LAMMPS. It uses tiny synthetic Lennard-Jones input files and records SimFlow
computation-stage artifacts, hashes, a credential scan, dry-run evidence, and a
checkpoint under a disposable project root.

Run:

```bash
python examples/lammps_safe_dry_run/run_example.py --project-root /tmp/simflow-lammps-demo
```

Expected behavior:

- `.simflow/` is initialized in the project root.
- LAMMPS input files are copied into `.simflow/artifacts/compute/lammps_safe/`.
- Computation evidence is recorded.
- `hpc_submit` remains blocked because no approval decision is recorded.
- No local, remote, or HPC job is submitted.
