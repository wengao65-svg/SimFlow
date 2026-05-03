#!/usr/bin/env python3
"""Dry-run validation for compute stage.

Checks input files, resource requests, and job script syntax
without actually submitting to HPC.
"""

import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.state import read_state
from lib.validator import load_stage_config


def check_input_files(input_manifest_path: str, base_dir: str = ".") -> dict:
    """Check that all input files exist and are non-empty."""
    with open(input_manifest_path, "r") as f:
        manifest = json.load(f)

    files = manifest.get("files", [])
    results = []
    all_ok = True

    for file_info in files:
        rel_path = file_info.get("path", "")
        full_path = os.path.join(base_dir, rel_path)
        exists = os.path.exists(full_path)
        non_empty = os.path.getsize(full_path) > 0 if exists else False

        status = "pass" if (exists and non_empty) else "fail"
        if status == "fail":
            all_ok = False

        results.append({
            "file": rel_path,
            "exists": exists,
            "non_empty": non_empty,
            "status": status,
        })

    return {
        "validator": "input_files",
        "status": "pass" if all_ok else "fail",
        "details": results,
    }


def check_resource_request(job_script_path: str) -> dict:
    """Check job script resource requests for reasonableness."""
    content = Path(job_script_path).read_text(encoding="utf-8", errors="replace")

    warnings = []
    # Check for excessive resource requests
    import re
    nodes_match = re.search(r"#SBATCH\s+--nodes=(\d+)", content)
    if nodes_match:
        nodes = int(nodes_match.group(1))
        if nodes > 64:
            warnings.append(f"Large node count: {nodes}")

    mem_match = re.search(r"#SBATCH\s+--mem=(\d+)([GgTt])", content)
    if mem_match:
        mem = int(mem_match.group(1))
        unit = mem_match.group(2).upper()
        if unit == "T" or (unit == "G" and mem > 500):
            warnings.append(f"Large memory request: {mem}{unit}")

    time_match = re.search(r"#SBATCH\s+--time=(\S+)", content)
    if time_match:
        time_str = time_match.group(1)
        warnings.append(f"Walltime: {time_str}")

    return {
        "validator": "resource_request",
        "status": "warning" if warnings else "pass",
        "message": "Resource check passed" if not warnings else f"Warnings: {warnings}",
        "details": {"warnings": warnings},
    }


def check_script_syntax(job_script_path: str) -> dict:
    """Basic syntax check for job scripts."""
    content = Path(job_script_path).read_text(encoding="utf-8", errors="replace")
    errors = []

    if not content.strip().startswith("#!"):
        errors.append("Missing shebang line")

    if "mpirun" not in content and "srun" not in content and "aprun" not in content:
        errors.append("No MPI launcher found (mpirun/srun/aprun)")

    return {
        "validator": "script_syntax",
        "status": "pass" if not errors else "fail",
        "message": "Syntax OK" if not errors else f"Errors: {errors}",
        "details": {"errors": errors},
    }


def run_dry_run(input_manifest_path: str, job_script_path: str, base_dir: str = ".") -> dict:
    """Run all dry-run checks."""
    checks = [
        check_input_files(input_manifest_path, base_dir),
        check_resource_request(job_script_path),
        check_script_syntax(job_script_path),
    ]

    overall = "pass"
    for c in checks:
        if c["status"] == "fail":
            overall = "fail"
            break
        elif c["status"] == "warning":
            overall = "warning"

    return {
        "dry_run": True,
        "overall": overall,
        "checks": checks,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: dry_run.py <input_manifest.json> <job_script.sh> [base_dir]")
        sys.exit(1)

    result = run_dry_run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
    print(json.dumps(result, indent=2))
