#!/usr/bin/env python3
"""Dry-run validation for compute stage.

Checks input files, resource requests, and job script syntax
without actually submitting to HPC.
"""

import sys
import json

from runtime.simflow_helpers.computation.dry_run import (
    check_input_files,
    check_resource_request,
    check_script_syntax,
    run_dry_run,
)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: dry_run.py <input_manifest.json> <job_script.sh> [base_dir]")
        sys.exit(1)

    result = run_dry_run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
    # Add actionable suggestions to warnings
    for check in result.get("checks", []):
        if check.get("status") == "fail" and "shebang" in check.get("message", "").lower():
            check["suggestion"] = "Add '#!/bin/bash' as the first line of the job script"
        if check.get("status") == "fail" and "mpi" in check.get("message", "").lower():
            check["suggestion"] = "Add 'mpirun -np N' or 'srun' to the job script"
        if check.get("status") == "warning" and "large node" in check.get("message", "").lower():
            check["suggestion"] = "Consider reducing node count for testing; increase for production"
    output = {
        "valid": result["overall"] == "pass",
        "issues": [c for c in result.get("checks", []) if c.get("status") == "fail"],
        "warnings": [c for c in result.get("checks", []) if c.get("status") == "warning"],
        "checks": result.get("checks", []),
    }
    print(json.dumps(output, indent=2))
