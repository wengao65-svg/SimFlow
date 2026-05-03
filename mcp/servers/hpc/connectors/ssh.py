"""SSH remote execution HPC connector."""

import os
import subprocess
from typing import Optional

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
        """Submit a job via SSH."""
        result = self.dry_run(script_path)
        if not result["valid"]:
            return {"success": False, "errors": result["issues"]}

        # Copy script to remote and execute
        remote_path = "/tmp/simflow_job_{}".format(os.path.basename(script_path))
        try:
            # Copy
            scp_cmd = ["scp"]
            if self.key_file:
                scp_cmd.extend(["-i", self.key_file])
            scp_cmd.extend([script_path, "{}:{}".format(self.host, remote_path)])

            proc = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return {"success": False, "errors": ["SCP failed: {}".format(proc.stderr)]}

            # Execute
            exec_cmd = self._ssh_cmd("nohup bash {} & echo $!".format(remote_path))
            proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=30)

            if proc.returncode == 0:
                pid = proc.stdout.strip().split("\n")[-1]
                return {"success": True, "job_id": pid, "scheduler": "ssh", "host": self.host}
            else:
                return {"success": False, "errors": [proc.stderr.strip()]}

        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["SSH operation timed out"]}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def status(self, job_id: str) -> dict:
        """Check remote process status."""
        try:
            cmd = self._ssh_cmd("kill -0 {} 2>/dev/null && echo running || echo completed".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            status = "running" if "running" in proc.stdout else "completed"
            return {"job_id": job_id, "status": status, "host": self.host, "scheduler": "ssh"}
        except Exception:
            return {"job_id": job_id, "status": "unknown"}

    def cancel(self, job_id: str) -> dict:
        """Kill a remote process."""
        try:
            cmd = self._ssh_cmd("kill -9 {}".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return {"success": proc.returncode == 0, "job_id": job_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
