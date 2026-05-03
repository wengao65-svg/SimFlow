"""SLURM HPC connector (dry-run focused, submit requires approval)."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseHPCConnector
from runtime.lib.hpc import generate_slurm_script, parse_slurm_job_id
from runtime.scripts.dry_run import run_dry_run


class SlurmConnector(BaseHPCConnector):
    """SLURM scheduler connector.

    Default mode: dry-run only.
    Real submission requires explicit approval via approval gate.
    """

    def dry_run(self, script_path: str, manifest_path: str = "", base_dir: str = ".") -> dict:
        """Validate a job script without submitting.

        Runs input file checks, resource request validation, and script syntax check.
        """
        if manifest_path:
            return run_dry_run(manifest_path, script_path, base_dir)

        # Basic script-only validation
        script = Path(script_path)
        if not script.exists():
            return {"status": "fail", "message": f"Script not found: {script_path}"}

        content = script.read_text(encoding="utf-8", errors="replace")
        checks = []

        # Shebang check
        if not content.strip().startswith("#!"):
            checks.append({"check": "shebang", "status": "fail", "message": "Missing shebang line"})
        else:
            checks.append({"check": "shebang", "status": "pass"})

        # SBATCH directives check
        sbatch_count = content.count("#SBATCH")
        checks.append({
            "check": "sbatch_directives",
            "status": "pass" if sbatch_count > 0 else "warning",
            "message": f"Found {sbatch_count} SBATCH directives",
        })

        # MPI launcher check
        has_mpi = any(launcher in content for launcher in ["mpirun", "srun", "mpiexec"])
        checks.append({
            "check": "mpi_launcher",
            "status": "pass" if has_mpi else "warning",
            "message": "MPI launcher found" if has_mpi else "No MPI launcher detected",
        })

        overall = "pass"
        for c in checks:
            if c["status"] == "fail":
                overall = "fail"
                break
            elif c["status"] == "warning":
                overall = "warning"

        return {"dry_run": True, "overall": overall, "checks": checks}

    def submit(self, script_path: str) -> dict:
        """Submit a job to SLURM.

        WARNING: This requires explicit approval. Returns error by default.
        """
        return {
            "status": "error",
            "message": "Real HPC submission requires approval gate. Use dry_run first.",
            "approval_required": True,
            "gate": "hpc_submit",
        }

    def status(self, job_id: str) -> dict:
        """Check SLURM job status."""
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "-h", "-o", "%T %M %N"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return {"status": "error", "message": f"squeue failed: {result.stderr.strip()}"}

            output = result.stdout.strip()
            if not output:
                return {"status": "success", "data": {"job_id": job_id, "state": "NOT_FOUND"}}

            parts = output.split()
            return {
                "status": "success",
                "data": {
                    "job_id": job_id,
                    "state": parts[0] if len(parts) > 0 else "unknown",
                    "runtime": parts[1] if len(parts) > 1 else None,
                    "nodes": parts[2] if len(parts) > 2 else None,
                },
            }
        except FileNotFoundError:
            return {"status": "error", "message": "squeue not found. SLURM may not be installed."}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "squeue timed out"}

    def cancel(self, job_id: str) -> dict:
        """Cancel a SLURM job."""
        try:
            result = subprocess.run(
                ["scancel", job_id],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return {"status": "success", "message": f"Job {job_id} cancelled"}
            return {"status": "error", "message": f"scancel failed: {result.stderr.strip()}"}
        except FileNotFoundError:
            return {"status": "error", "message": "scancel not found. SLURM may not be installed."}
