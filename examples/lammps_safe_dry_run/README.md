# LAMMPS Compact Dry-Run Example

This example copies tiny synthetic LAMMPS inputs into a normal calculation
directory, prepares an immutable local run plan, confirms that unapproved
submit is blocked, and records the package once as a logical deliverable.

```bash
python examples/lammps_safe_dry_run/run_example.py --project-root /tmp/simflow-lammps-demo
```

No LAMMPS process runs. No legacy registries or automatic checkpoints are
created. Credential scan results are embedded in the immutable run-plan report.
