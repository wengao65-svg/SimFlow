"""Base connector for HPC schedulers."""

from abc import ABC, abstractmethod


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
