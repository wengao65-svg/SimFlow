"""PBS/qsub HPC connector."""

import re
import subprocess
from typing import Optional

from .base import BaseHPCConnector


class PBSConnector(BaseHPCConnector):
    """Connector for PBS/Torque job scheduler."""

    def dry_run(self, script_path: str) -> dict:
        """Validate a PBS job script without submitting."""
        issues = []
        try:
            with open(script_path) as f:
                content = f.read()

            if "#PBS" not in content:
                issues.append("No #PBS directives found")

            if not content.strip().startswith("#!"):
                issues.append("Missing shebang line")

            # Check for required PBS directives
            has_walltime = "#PBS -l walltime" in content
            has_nodes = "#PBS -l nodes" in content or "#PBS -l select" in content

            if not has_walltime:
                issues.append("Missing walltime specification")
            if not has_nodes:
                issues.append("Missing node specification")

        except FileNotFoundError:
            issues.append("Script file not found: {}".format(script_path))

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "scheduler": "pbs",
            "script": script_path,
        }

    def submit(self, script_path: str) -> dict:
        """Submit a PBS job."""
        result = self.dry_run(script_path)
        if not result["valid"]:
            return {"success": False, "errors": result["issues"]}

        try:
            proc = subprocess.run(
                ["qsub", script_path],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                job_id = proc.stdout.strip()
                return {"success": True, "job_id": job_id, "scheduler": "pbs"}
            else:
                return {"success": False, "errors": [proc.stderr.strip()]}
        except FileNotFoundError:
            return {"success": False, "errors": ["qsub command not found"]}
        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["qsub timed out"]}

    def status(self, job_id: str) -> dict:
        """Check PBS job status."""
        try:
            proc = subprocess.run(
                ["qstat", "-f", job_id],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                return {"status": "unknown", "error": proc.stderr.strip()}

            output = proc.stdout
            state_match = re.search(r"job_state = (\w)", output)
            state_map = {"Q": "queued", "R": "running", "C": "completed",
                         "E": "exiting", "H": "held", "S": "suspended"}

            state = state_map.get(state_match.group(1), "unknown") if state_match else "unknown"

            return {"job_id": job_id, "status": state, "scheduler": "pbs"}
        except FileNotFoundError:
            return {"status": "unknown", "error": "qstat command not found"}

    def cancel(self, job_id: str) -> dict:
        """Cancel a PBS job."""
        try:
            proc = subprocess.run(
                ["qdel", job_id],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                return {"success": True, "job_id": job_id}
            else:
                return {"success": False, "error": proc.stderr.strip()}
        except FileNotFoundError:
            return {"success": False, "error": "qdel command not found"}
