# SimFlow Compact Dry-Run Example

This redistributable example prepares a tiny local job script and input,
creates an immutable `hpc/plan`, confirms that submit is blocked without
approval, and appends one logical milestone record.

```bash
python examples/safe_dry_run/run_example.py --project-root /tmp/simflow-safe-demo
```

It creates `.simflow/project.json`, `.simflow/records.jsonl`, one run-plan
report, and one summary report. It does not create legacy state registries,
checkpoints, or real jobs.
