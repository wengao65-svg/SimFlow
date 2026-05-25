# SimFlow Safe Dry-Run Example

This example is the small, redistributable smoke path for real users and CI.
It does not require licensed potentials, proprietary files, remote access, or
HPC credentials.

Run it into a disposable project directory:

```bash
python examples/safe_dry_run/run_example.py --project-root /tmp/simflow-safe-demo
```

The script initializes a SimFlow project, runs the canonical workflow stages
through `writing`, and produces `.simflow/` state, artifacts, checkpoints,
computation submit-readiness evidence, and handoff reports. The computation
stage remains dry-run only; no local, remote, or HPC job is submitted.
