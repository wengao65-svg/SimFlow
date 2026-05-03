"""SLURM HPC connector.

Supports dry-run validation, real sbatch submission (with approval gate),
squeue + sacct status checking, and job cancellation.
"""

import re
import subprocess
from pathlib import Path

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

    def submit(self, script_path: str, approved: bool = False) -> dict:
        """Submit a job to SLURM via sbatch.

        Args:
            script_path: Path to the SLURM submission script
            approved: Must be True to actually submit (approval gate)

        Returns:
            dict with status, job_id (on success), or approval_required
        """
        if not approved:
            return {
                "status": "error",
                "message": "Real HPC submission requires approval gate. Use dry_run first.",
                "approval_required": True,
                "gate": "hpc_submit",
            }

        script = Path(script_path)
        if not script.exists():
            return {"status": "error", "message": f"Script not found: {script_path}"}

        try:
            result = subprocess.run(
                ["sbatch", str(script)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return {"status": "error", "message": f"sbatch failed: {result.stderr.strip()}"}

            # Parse "Submitted batch job 12345"
            job_id = parse_slurm_job_id(result.stdout.strip())
            if not job_id:
                return {
                    "status": "error",
                    "message": f"sbatch succeeded but could not parse job ID from: {result.stdout.strip()}",
                }

            return {"status": "success", "job_id": job_id, "message": f"Submitted batch job {job_id}"}

        except FileNotFoundError:
            return {"status": "error", "message": "sbatch not found. SLURM may not be installed."}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "sbatch timed out"}

    def status(self, job_id: str) -> dict:
        """Check SLURM job status.

        First tries squeue (active jobs). If not found, falls back to
        sacct for completed/failed/cancelled jobs.
        """
        # Try squeue first (active jobs)
        squeue_result = self._squeue_status(job_id)
        if squeue_result is not None:
            return squeue_result

        # Fallback to sacct (finished jobs)
        sacct_result = self._sacct_status(job_id)
        if sacct_result is not None:
            return sacct_result

        return {
            "status": "success",
            "data": {"job_id": job_id, "state": "NOT_FOUND"},
        }

    def _squeue_status(self, job_id: str) -> dict | None:
        """Query squeue for active job status. Returns None if job not in queue."""
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "-h", "-o", "%T %M %N"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None

            output = result.stdout.strip()
            if not output:
                return None

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
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _sacct_status(self, job_id: str) -> dict | None:
        """Query sacct for completed job status. Returns None if not found."""
        try:
            result = subprocess.run(
                [
                    "sacct", "-j", job_id,
                    "--format=State,Elapsed,ExitCode,Start,End",
                    "--noheader", "--parsable2",
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None

            output = result.stdout.strip()
            if not output:
                return None

            # Take first non-batch line (skip .batch/.extern steps)
            for line in output.split("\n"):
                line = line.strip()
                if not line or ".batch" in line or ".extern" in line:
                    continue
                parts = line.split("|")
                state = parts[0] if len(parts) > 0 else "unknown"
                elapsed = parts[1] if len(parts) > 1 else None
                exit_code = parts[2] if len(parts) > 2 else None
                start = parts[3] if len(parts) > 3 else None
                end = parts[4] if len(parts) > 4 else None

                return {
                    "status": "success",
                    "data": {
                        "job_id": job_id,
                        "state": state,
                        "elapsed": elapsed,
                        "exit_code": exit_code,
                        "start": start,
                        "end": end,
                    },
                }

            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

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
