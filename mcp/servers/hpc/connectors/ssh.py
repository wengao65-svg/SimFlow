"""SSH remote execution HPC connector.

Supports two modes:
- SLURM-aware: detects remote SLURM and uses sbatch
- Plain nohup: falls back to nohup bash for non-SLURM hosts
"""

import os
import subprocess
from pathlib import Path

from .base import BaseHPCConnector


class SSHConnector(BaseHPCConnector):
    """Connector for SSH-based remote execution."""

    def __init__(self, host: str = None, user: str = None, key_file: str = None):
        self.host = host or os.environ.get("SIMFLOW_SSH_HOST")
        self.user = user or os.environ.get("SIMFLOW_SSH_USER")
        self.key_file = key_file or os.environ.get("SIMFLOW_SSH_KEY")

    def _ssh_cmd(self, remote_cmd: str) -> list:
        """Build SSH command."""
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.key_file:
            cmd.extend(["-i", self.key_file])
        target = "{}@{}".format(self.user, self.host) if self.user else self.host
        cmd.extend([target, remote_cmd])
        return cmd

    def _scp_cmd(self, src: str, dst: str) -> list:
        """Build SCP command."""
        cmd = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.key_file:
            cmd.extend(["-i", self.key_file])
        cmd.extend([src, dst])
        return cmd

    def _remote_has_slurm(self) -> bool:
        """Check if the remote host has SLURM (sbatch) available."""
        try:
            cmd = self._ssh_cmd("which sbatch >/dev/null 2>&1 && echo yes || echo no")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return "yes" in proc.stdout
        except Exception:
            return False

    def dry_run(self, script_path: str) -> dict:
        """Validate a script exists locally."""
        issues = []
        if not self.host:
            issues.append("No SSH host configured (set SIMFLOW_SSH_HOST)")

        try:
            if not os.path.exists(script_path):
                issues.append("Script not found locally: {}".format(script_path))
        except Exception:
            pass

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "scheduler": "ssh",
            "host": self.host,
            "script": script_path,
        }

    def submit(self, script_path: str) -> dict:
        """Submit a job via SSH.

        Detects whether the remote host has SLURM:
        - If SLURM: copies script and uses sbatch
        - If no SLURM: copies script and uses nohup bash
        """
        result = self.dry_run(script_path)
        if not result["valid"]:
            return {"success": False, "errors": result["issues"]}

        remote_path = "/tmp/simflow_job_{}".format(os.path.basename(script_path))
        try:
            # Copy script to remote
            scp_cmd = self._scp_cmd(
                script_path,
                "{}:{}".format(self.host, remote_path),
            )
            proc = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return {"success": False, "errors": ["SCP failed: {}".format(proc.stderr)]}

            if self._remote_has_slurm():
                # Submit via sbatch
                exec_cmd = self._ssh_cmd("sbatch {}".format(remote_path))
                proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    # Parse "Submitted batch job 12345"
                    from runtime.lib.hpc import parse_slurm_job_id
                    job_id = parse_slurm_job_id(proc.stdout.strip())
                    if job_id:
                        return {
                            "success": True,
                            "job_id": job_id,
                            "scheduler": "slurm",
                            "host": self.host,
                        }
                    return {
                        "success": True,
                        "job_id": proc.stdout.strip(),
                        "scheduler": "slurm",
                        "host": self.host,
                    }
                return {"success": False, "errors": [proc.stderr.strip()]}
            else:
                # Fallback to nohup bash
                exec_cmd = self._ssh_cmd("nohup bash {} & echo $!".format(remote_path))
                proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    pid = proc.stdout.strip().split("\n")[-1]
                    return {"success": True, "job_id": pid, "scheduler": "ssh", "host": self.host}
                return {"success": False, "errors": [proc.stderr.strip()]}

        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["SSH operation timed out"]}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def status(self, job_id: str) -> dict:
        """Check remote job status.

        For SLURM jobs: uses squeue then sacct.
        For nohup jobs: checks if PID is alive.
        """
        # Try SLURM status first
        try:
            cmd = self._ssh_cmd(
                "squeue -j {} -h -o '%T %M %N' 2>/dev/null".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.strip().split()
                return {
                    "status": "success",
                    "data": {
                        "job_id": job_id,
                        "state": parts[0] if len(parts) > 0 else "unknown",
                        "runtime": parts[1] if len(parts) > 1 else None,
                        "nodes": parts[2] if len(parts) > 2 else None,
                        "scheduler": "slurm",
                    },
                }

            # Fallback to sacct
            cmd = self._ssh_cmd(
                "sacct -j {} --format=State,Elapsed,ExitCode --noheader --parsable2 "
                "2>/dev/null | head -1".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.strip().split("|")
                if parts and parts[0]:
                    return {
                        "status": "success",
                        "data": {
                            "job_id": job_id,
                            "state": parts[0],
                            "elapsed": parts[1] if len(parts) > 1 else None,
                            "exit_code": parts[2] if len(parts) > 2 else None,
                            "scheduler": "slurm",
                        },
                    }
        except Exception:
            pass

        # Fallback: check PID
        try:
            cmd = self._ssh_cmd(
                "kill -0 {} 2>/dev/null && echo running || echo completed".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            status = "running" if "running" in proc.stdout else "completed"
            return {
                "status": "success",
                "data": {"job_id": job_id, "state": status, "scheduler": "ssh", "host": self.host},
            }
        except Exception:
            return {"status": "success", "data": {"job_id": job_id, "state": "unknown"}}

    def cancel(self, job_id: str) -> dict:
        """Cancel a remote job (SLURM scancel or kill)."""
        # Try scancel first
        try:
            cmd = self._ssh_cmd("scancel {} 2>/dev/null".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0:
                return {"success": True, "job_id": job_id, "scheduler": "slurm"}
        except Exception:
            pass

        # Fallback to kill
        try:
            cmd = self._ssh_cmd("kill -9 {}".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return {"success": proc.returncode == 0, "job_id": job_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_files(self, local_dir: str, remote_dir: str, files: list[str]) -> dict:
        """Upload files to remote host via SCP."""
        if not self.host:
            return {"status": "error", "message": "No SSH host configured"}

        errors = []
        for fname in files:
            local_path = os.path.join(local_dir, fname)
            remote_path = "{}:{}/{}".format(self.host, remote_dir, fname)
            try:
                cmd = self._scp_cmd(local_path, remote_path)
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if proc.returncode != 0:
                    errors.append(f"Failed to upload {fname}: {proc.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout uploading {fname}")
            except Exception as e:
                errors.append(f"Error uploading {fname}: {e}")

        if errors:
            return {"status": "error", "errors": errors}
        return {"status": "success", "uploaded": len(files)}

    def download_files(self, remote_dir: str, local_dir: str, files: list[str]) -> dict:
        """Download files from remote host via SCP."""
        if not self.host:
            return {"status": "error", "message": "No SSH host configured"}

        errors = []
        for fname in files:
            remote_path = "{}:{}/{}".format(self.host, remote_dir, fname)
            local_path = os.path.join(local_dir, fname)
            try:
                cmd = self._scp_cmd(remote_path, local_path)
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode != 0:
                    errors.append(f"Failed to download {fname}: {proc.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout downloading {fname}")
            except Exception as e:
                errors.append(f"Error downloading {fname}: {e}")

        if errors:
            return {"status": "error", "errors": errors}
        return {"status": "success", "downloaded": len(files)}
