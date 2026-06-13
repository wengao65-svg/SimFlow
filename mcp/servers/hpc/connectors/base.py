"""Base connector for HPC schedulers."""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from runtime.simflow_core.gates import check_gate, get_gate_decisions
from runtime.simflow_core.state import ProjectRootError, read_state, resolve_project_root


class BaseHPCConnector(ABC):
    """Abstract base for HPC scheduler connectors."""

    @abstractmethod
    def dry_run(self, script_path: str) -> dict:
        """Validate a job script without submitting."""
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

    def _resolve_evidence_path(self, project_root: Path, evidence_path: str) -> Path | None:
        candidate = Path(evidence_path).expanduser()
        candidates = [candidate] if candidate.is_absolute() else [
            project_root / candidate,
            project_root / ".simflow" / candidate,
            project_root / ".simflow" / "artifacts" / candidate,
            project_root / ".simflow" / "reports" / candidate,
        ]
        for path in candidates:
            if path.exists():
                return path.resolve()
        return None

    def _first_present(self, payload: dict, paths: list[str]):
        for path in paths:
            current = payload
            found = True
            for part in path.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    found = False
                    break
            if found:
                return current
        return None

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
        dry_run_evidence: Optional[str] = None,
        script_hash: Optional[str] = None,
        input_artifact_hash: Optional[str] = None,
        approved: Optional[bool] = None,
    ) -> dict:
        """Validate approval, dry-run evidence, and hashes before real execution."""
        script = Path(script_path)
        if not script.exists():
            return {"status": "error", "message": f"Script not found: {script_path}"}

        if not approval_token and not gate_decision_id:
            message = "Submit requires approval_token or gate_decision_id from the hpc_submit gate."
            if approved is not None:
                message = "Boolean approved is not accepted; " + message
            return self._approval_error(message)

        if not dry_run_evidence:
            return self._approval_error(
                "Submit requires dry_run_evidence recorded from the reviewed dry-run.",
                code="dry_run_evidence_required",
            )
        if not script_hash:
            return self._approval_error(
                "Submit requires the approved job script sha256 hash.",
                code="script_hash_required",
            )
        if not input_artifact_hash:
            return self._approval_error(
                "Submit requires the approved input artifact or manifest hash.",
                code="input_artifact_hash_required",
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
        if not read_state(project_root=str(root), state_file="workflow.json"):
            return {
                "status": "error",
                "message": "Submit requires an initialized SimFlow workflow under project_root.",
                "code": "missing_workflow_state",
            }

        current_script_hash = self._sha256_file(script)
        if current_script_hash != script_hash:
            return self._approval_error(
                "Current job script hash does not match the approved script_hash.",
                code="script_hash_mismatch",
                current_script_hash=current_script_hash,
                approved_script_hash=script_hash,
            )

        evidence_path = self._resolve_evidence_path(root, dry_run_evidence)
        if evidence_path is None:
            return self._approval_error(
                "Dry-run evidence file was not found under project_root/.simflow.",
                code="dry_run_evidence_missing",
            )
        try:
            dry_run = json.loads(evidence_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._approval_error(
                f"Dry-run evidence is not valid JSON: {exc}",
                code="dry_run_evidence_invalid",
            )

        dry_run_status = dry_run.get("status", dry_run.get("overall"))
        if dry_run_status not in ("pass", "warning"):
            return self._approval_error(
                "Dry-run evidence status does not allow real submission.",
                code="dry_run_not_passed",
                dry_run_status=dry_run_status,
            )

        dry_run_script_hash = self._first_present(dry_run, [
            "script_hash",
            "job_script_hash",
            "hashes.job_script",
            "hashes.script",
            "script.sha256",
            "job_script.sha256",
        ])
        if dry_run_script_hash != script_hash:
            return self._approval_error(
                "Job script hash does not match the dry-run evidence.",
                code="dry_run_script_hash_mismatch",
                dry_run_script_hash=dry_run_script_hash,
                approved_script_hash=script_hash,
            )

        dry_run_input_hash = self._first_present(dry_run, [
            "input_artifact_hash",
            "input_manifest_hash",
            "hashes.input_artifact",
            "hashes.input_manifest",
            "input.sha256",
            "manifest.sha256",
        ])
        if dry_run_input_hash != input_artifact_hash:
            return self._approval_error(
                "Input artifact hash does not match the dry-run evidence.",
                code="dry_run_input_hash_mismatch",
                dry_run_input_hash=dry_run_input_hash,
                approved_input_artifact_hash=input_artifact_hash,
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

        gate_result = check_gate("hpc_submit", {"project_root": str(root)})
        if gate_result["status"] != "pass":
            return self._approval_error(
                "hpc_submit gate is blocked by missing or failing evidence.",
                code="hpc_submit_gate_blocked",
                gate_result=gate_result,
            )

        return {
            "status": "success",
            "project_root": str(root),
            "gate_decision_id": matching_decision.get("decision_id"),
            "dry_run_evidence_path": str(evidence_path),
            "script_hash": current_script_hash,
            "input_artifact_hash": input_artifact_hash,
        }
