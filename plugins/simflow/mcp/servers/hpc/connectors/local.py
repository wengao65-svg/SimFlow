"""Local shell HPC connector."""

import os
import subprocess
from typing import Optional

from .base import BaseHPCConnector


class LocalConnector(BaseHPCConnector):
    """Connector for local shell execution."""

    def dry_run(self, script_path: str) -> dict:
        """Validate a job script without executing."""
        issues = []
        try:
            with open(script_path) as f:
                content = f.read()

            if not content.strip().startswith("#!"):
                issues.append("Missing shebang line")

            if not os.access(script_path, os.X_OK):
                issues.append("Script is not executable")

        except FileNotFoundError:
            issues.append("Script file not found: {}".format(script_path))

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "scheduler": "local",
            "script": script_path,
        }

    def submit(self, script_path: str, timeout: int = 3600) -> dict:
        """Execute a script locally."""
        result = self.dry_run(script_path)
        if not result["valid"]:
            return {"success": False, "errors": result["issues"]}

        try:
            proc = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True, timeout=timeout,
                cwd=os.path.dirname(os.path.abspath(script_path)),
            )
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "scheduler": "local",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["Execution timed out after {}s".format(timeout)]}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def status(self, job_id: str) -> dict:
        """Check local process status (job_id is PID)."""
        try:
            pid = int(job_id)
            os.kill(pid, 0)
            return {"job_id": job_id, "status": "running", "scheduler": "local"}
        except ProcessLookupError:
            return {"job_id": job_id, "status": "completed", "scheduler": "local"}
        except ValueError:
            return {"job_id": job_id, "status": "unknown", "error": "Invalid PID"}
        except PermissionError:
            return {"job_id": job_id, "status": "running", "scheduler": "local"}

    def cancel(self, job_id: str) -> dict:
        """Cancel a local process (kill PID)."""
        try:
            pid = int(job_id)
            os.kill(pid, 9)  # SIGKILL
            return {"success": True, "job_id": job_id}
        except ProcessLookupError:
            return {"success": True, "job_id": job_id, "message": "Process already exited"}
        except ValueError:
            return {"success": False, "error": "Invalid PID"}
        except PermissionError:
            return {"success": False, "error": "Permission denied"}
