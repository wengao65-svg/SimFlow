"""Base connector for HPC schedulers."""

import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from runtime.simflow_core.gates import get_gate_decisions
from runtime.simflow_core.state import ProjectRootError, resolve_project_root

try:
    from run_plan import RunPlanError, validate_run_plan_current
except ModuleNotFoundError:  # pragma: no cover - package import path
    from ..run_plan import RunPlanError, validate_run_plan_current


class BaseHPCConnector(ABC):
    """Abstract base for HPC scheduler connectors."""

    @abstractmethod
    def dry_run(self, script_path: str, manifest_path: str = "", base_dir: str = ".") -> dict:
        """Validate a job script without submitting.

        All connectors must accept manifest_path and base_dir for polymorphism,
        even if they ignore them (local, ssh, pbs).
        """
        ...

    @abstractmethod
    def submit(self, script_path: str, **kwargs) -> dict:
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

    def _sha256_file(self, path: str | Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _approval_error(self, message: str, code: str = "approval_required", **extra) -> dict:
        result = {
            "status": "error",
            "message": message,
            "approval_required": True,
            "gate": "hpc_submit",
            "code": code,
        }
        result.update(extra)
        return result

    def validate_submit_authorization(
        self,
        script_path: str,
        *,
        project_root: Optional[str] = None,
        approval_token: Optional[str] = None,
        gate_decision_id: Optional[str] = None,
        run_plan_hash: Optional[str] = None,
        expected_scheduler: Optional[str] = None,
        approval_bindings: Optional[dict] = None,
        approved: Optional[bool] = None,
    ) -> dict:
        """Validate an unchanged run plan and its recorded approval."""
        script = Path(script_path)
        if not script.exists():
            return {"status": "error", "message": f"Script not found: {script_path}"}

        if not approval_token and not gate_decision_id:
            message = "Submit requires approval_token or gate_decision_id from the hpc_submit gate."
            if approved is not None:
                message = "Boolean approved is not accepted; " + message
            return self._approval_error(message)
        if not run_plan_hash:
            return self._approval_error(
                "Submit requires an immutable run_plan_hash produced by hpc/plan.",
                code="run_plan_hash_required",
            )
        if not project_root:
            return {
                "status": "error",
                "message": "project_root is required for approval-aware submit.",
                "code": "project_root_required",
            }

        try:
            root = resolve_project_root(project_root=project_root)
        except ProjectRootError as exc:
            return {"status": "error", "message": str(exc), "code": "invalid_project_root"}
        try:
            plan = validate_run_plan_current(str(root), run_plan_hash)
        except (RunPlanError, OSError, ValueError) as exc:
            return self._approval_error(
                str(exc),
                code="run_plan_stale",
                run_plan_hash=run_plan_hash,
            )
        planned_script = (root / plan["script"]["path"]).resolve()
        if script.resolve() != planned_script:
            return self._approval_error(
                "Submitted script path does not match the immutable run plan.",
                code="run_plan_script_mismatch",
            )
        if expected_scheduler and plan.get("scheduler") != expected_scheduler:
            return self._approval_error(
                "Connector scheduler does not match the immutable run plan.",
                code="run_plan_scheduler_mismatch",
            )

        decisions = get_gate_decisions("hpc_submit", project_root=str(root))
        approval_id = gate_decision_id or approval_token
        matching_decision = None
        for decision in decisions:
            conditions = decision.get("conditions", {})
            if (
                decision.get("decision_id") == approval_id
                or decision.get("approval_token") == approval_id
                or conditions.get("approval_token") == approval_id
            ):
                matching_decision = decision
                break
        if not matching_decision or matching_decision.get("decision") != "approved":
            return self._approval_error(
                "No approved hpc_submit gate decision matched the provided approval reference.",
                code="gate_decision_not_approved",
                gate_decision_id=gate_decision_id,
            )

        decision_conditions = matching_decision.get("conditions", {})
        if not isinstance(decision_conditions, dict):
            decision_conditions = {}
        if decision_conditions.get("run_plan_hash") != run_plan_hash:
            return self._approval_error(
                "Approved hpc_submit gate decision is not bound to this run_plan_hash.",
                code="run_plan_approval_mismatch",
                gate_decision_id=matching_decision.get("decision_id"),
            )
        expected_bindings = approval_bindings or {}
        mismatched_bindings = {
            name: {
                "planned": plan.get(name),
                "submitted": value,
            }
            for name, value in expected_bindings.items()
            if plan.get(name) != value
        }
        if mismatched_bindings:
            return self._approval_error(
                "Runtime bindings do not match the immutable run plan.",
                code="run_plan_binding_mismatch",
                gate_decision_id=matching_decision.get("decision_id"),
                mismatches=mismatched_bindings,
            )

        return {
            "status": "success",
            "project_root": str(root),
            "gate_decision_id": matching_decision.get("decision_id"),
            "run_plan_hash": run_plan_hash,
            "script_hash": plan["script"]["sha256"],
            "run_plan": plan,
        }
