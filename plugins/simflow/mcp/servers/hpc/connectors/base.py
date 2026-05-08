"""Base connector for HPC schedulers."""

import time
from abc import ABC, abstractmethod
from typing import Optional


class BaseHPCConnector(ABC):
    """Abstract base for HPC scheduler connectors."""

    @abstractmethod
    def dry_run(self, script_path: str) -> dict:
        """Validate a job script without submitting."""
        ...

    @abstractmethod
    def submit(self, script_path: str) -> dict:
        """Submit a job to the scheduler."""
        ...

    @abstractmethod
    def status(self, job_id: str) -> dict:
        """Check job status."""
        ...

    @abstractmethod
    def cancel(self, job_id: str) -> dict:
        """Cancel a running job."""
        ...

    def wait(
        self,
        job_id: str,
        poll_interval: int = 30,
        timeout: int = 3600,
    ) -> dict:
        """Poll job status until terminal state or timeout.

        Args:
            job_id: Job identifier
            poll_interval: Seconds between polls
            timeout: Max seconds to wait

        Returns:
            Final status dict with 'state' key
        """
        start = time.time()
        while time.time() - start < timeout:
            result = self.status(job_id)
            state = ""
            if isinstance(result, dict):
                data = result.get("data", result)
                state = data.get("state", "")
            if state.upper() in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NOT_FOUND"):
                return result
            time.sleep(poll_interval)
        return {"status": "timeout", "message": f"Timed out after {timeout}s waiting for {job_id}"}

    def upload_files(
        self, local_dir: str, remote_dir: str, files: list[str]
    ) -> dict:
        """Upload files to remote host. Override for SSH-based connectors."""
        return {"status": "error", "message": "upload_files not supported by this connector"}

    def download_files(
        self, remote_dir: str, local_dir: str, files: list[str]
    ) -> dict:
        """Download files from remote host. Override for SSH-based connectors."""
        return {"status": "error", "message": "download_files not supported by this connector"}
