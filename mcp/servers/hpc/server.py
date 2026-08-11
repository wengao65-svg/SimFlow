"""HPC MCP Server.

Provides HPC job management tools.
Supports multiple schedulers: slurm, pbs, local, ssh.
Default mode: dry-run only. Real submission requires approval gate.
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.slurm import SlurmConnector
from connectors.pbs import PBSConnector
from connectors.local import LocalConnector
from broker import SSHBrokerClient
from mcp.shared.transport import dispatch_request, run_server
from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.gates import check_gate, get_gate_decisions
from runtime.simflow_helpers.computation.job_records import record_submit_job
from transfer import (
    TransferValidationError,
    expand_local_paths,
    file_manifest,
    manifests_match,
    normalize_target,
    request_fingerprint,
    restricted_transfer_files,
    resolve_project_path,
    validate_remote_dir,
)


_CONNECTORS = {
    "slurm": SlurmConnector,
    "pbs": PBSConnector,
    "local": LocalConnector,
    "ssh": SSHBrokerClient,
}

_default = None


def _get_connector(scheduler: str = "auto", target: dict | None = None):
    """Get a connector instance, with auto-detection and fallback.

    Auto-detection order:
    1. SIMFLOW_SLURM_HOST set -> SlurmConnector
    2. Per-call target -> SSHBrokerClient
    3. Fallback -> LocalConnector
    """
    if target is not None:
        normalized = normalize_target(target)
        if scheduler not in ("auto", "ssh"):
            return None
        return SSHBrokerClient(**normalized)
    if scheduler == "auto":
        # Lazy-import os to avoid global side effects at module load
        import os as _os
        if _os.environ.get("SIMFLOW_SLURM_HOST"):
            return SlurmConnector()
        # Default fallback: local shell
        return LocalConnector()
    if scheduler == "ssh":
        return None
    cls = _CONNECTORS.get(scheduler)
    if cls is None:
        return None
    try:
        return cls()
    except Exception:
        return LocalConnector()


def handle_dry_run(params: dict) -> dict:
    """Validate a job script without submitting."""
    script_path = params.get("script_path", "")
    manifest_path = params.get("manifest_path", "")
    base_dir = params.get("base_dir", ".")
    scheduler = params.get("scheduler", "auto")
    if not script_path:
        return {"status": "error", "message": "script_path is required"}
    if scheduler == "ssh" and not params.get("target"):
        return {"status": "error", "message": "target is required for SSH dry-run", "code": "target_required"}

    try:
        connector = _get_connector(scheduler, params.get("target"))
    except TransferValidationError as exc:
        return {"status": "error", "message": str(exc), "code": "invalid_target"}
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler), "code": "unknown_scheduler"}

    result = connector.dry_run(script_path, manifest_path, base_dir)
    if result.get("status") == "error" or result.get("success") is False or result.get("valid") is False:
        return {
            "status": "error",
            "message": result.get("message") or "HPC dry-run validation failed",
            "data": result,
        }
    return {"status": "success", "data": result}


def handle_prepare(params: dict) -> dict:
    """Prepare a job script (generate SLURM script)."""
    from runtime.simflow_core.hpc import generate_slurm_script

    job_name = params.get("job_name", "simflow_job")
    executable = params.get("executable", "vasp_std")
    nodes = params.get("nodes", 1)
    ntasks = params.get("ntasks", 16)
    walltime = params.get("walltime", "04:00:00")

    script = generate_slurm_script(
        job_name=job_name,
        executable=executable,
        nodes=nodes,
        ntasks=ntasks,
        time=walltime,
    )
    return {"status": "success", "data": {"script": script, "job_name": job_name}}


def handle_status(params: dict) -> dict:
    """Check job status."""
    job_id = params.get("job_id", "")
    scheduler = params.get("scheduler", "auto")
    if not job_id:
        return {"status": "error", "message": "job_id is required"}
    if scheduler == "ssh" and not params.get("target"):
        return {"status": "error", "message": "target is required for SSH status", "code": "target_required"}

    try:
        connector = _get_connector(scheduler, params.get("target"))
    except TransferValidationError as exc:
        return {"status": "error", "message": str(exc), "code": "invalid_target"}
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler), "code": "unknown_scheduler"}

    result = connector.status(job_id)
    return result


def handle_submit(params: dict) -> dict:
    """Submit a job after approval, dry-run evidence, and hash validation."""
    script_path = params.get("script_path", "")
    scheduler = params.get("scheduler", "auto")
    if not script_path:
        return {"status": "error", "message": "script_path is required"}
    if not params.get("project_root"):
        return {"status": "error", "message": "project_root is required"}
    if not (params.get("approval_token") or params.get("gate_decision_id")):
        return {
            "status": "error",
            "message": "approval_token or gate_decision_id is required",
            "approval_required": True,
            "gate": "hpc_submit",
        }
    if not params.get("dry_run_evidence"):
        return {"status": "error", "message": "dry_run_evidence is required"}
    if not params.get("script_hash"):
        return {"status": "error", "message": "script_hash is required"}
    if not params.get("input_artifact_hash"):
        return {"status": "error", "message": "input_artifact_hash is required"}

    target = params.get("target")
    if scheduler == "ssh" and not target:
        return {"status": "error", "message": "target is required for SSH submit", "code": "target_required"}
    try:
        connector = _get_connector(scheduler, target)
    except TransferValidationError as exc:
        return {"status": "error", "message": str(exc), "code": "invalid_target"}
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler), "code": "unknown_scheduler"}
    if isinstance(connector, SSHBrokerClient) and not params.get("transfer_manifest"):
        return {
            "status": "error",
            "message": "SSH submit requires a verified transfer_manifest from hpc/upload",
            "code": "transfer_manifest_required",
        }

    submit_kwargs = {
        "project_root": params.get("project_root"),
        "approval_token": params.get("approval_token"),
        "gate_decision_id": params.get("gate_decision_id"),
        "dry_run_evidence": params.get("dry_run_evidence"),
        "script_hash": params.get("script_hash"),
        "input_artifact_hash": params.get("input_artifact_hash"),
    }
    if isinstance(connector, SSHBrokerClient):
        try:
            remote_workdir = validate_remote_dir(params.get("remote_workdir", ""))
        except TransferValidationError as exc:
            return {"status": "error", "message": str(exc), "code": "remote_workdir_invalid"}
        submit_kwargs["transfer_manifest"] = params.get("transfer_manifest")
        submit_kwargs["remote_workdir"] = remote_workdir
        submit_kwargs["target"] = connector.target
    if scheduler == "local":
        submit_kwargs["timeout"] = params.get("timeout", 3600)
    result = connector.submit(script_path, **submit_kwargs)
    if result.get("status") == "success" or result.get("success") is True:
        job_id = result.get("job_id")
        effective_scheduler = result.get("scheduler") or scheduler
        if not job_id:
            script_hash = result.get("script_hash") or params.get("script_hash") or "unknown"
            job_id = f"local_{script_hash[:12]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            result["job_id"] = job_id
        record_status = "completed" if effective_scheduler == "local" and result.get("returncode") is not None else "submitted"
        record = record_submit_job(
            project_root=params["project_root"],
            scheduler=effective_scheduler,
            job_id=str(job_id),
            status=record_status,
            script_path=script_path,
            gate_decision_id=result.get("gate_decision_id") or params.get("gate_decision_id"),
            dry_run_evidence=params.get("dry_run_evidence"),
            script_hash=result.get("script_hash") or params.get("script_hash"),
            input_artifact_hash=params.get("input_artifact_hash"),
            submit_result=result,
        )
        if record["status"] == "success":
            result["job_record_artifact_id"] = record["artifact"]["artifact_id"]
            result["job_record_path"] = record["path"]
        else:
            result["job_record_error"] = record
    return result


def _transfer_decision(params: dict, direction: str, remote_dir: str, paths: list[str], target: dict) -> dict:
    """Require a recorded hpc_transfer approval bound to this request."""
    project_root = params["project_root"]
    reference = params.get("gate_decision_id") or params.get("approval_token")
    fingerprint = request_fingerprint(direction, remote_dir, paths, target)
    if not reference:
        return {
            "status": "error",
            "message": "upload/download requires an approved hpc_transfer gate decision",
            "approval_required": True,
            "gate": "hpc_transfer",
            "transfer_request_hash": fingerprint,
        }

    matching = None
    for decision in get_gate_decisions("hpc_transfer", project_root=project_root):
        conditions = decision.get("conditions", {})
        if (
            decision.get("decision_id") == reference
            or conditions.get("approval_token") == reference
        ):
            matching = decision
            break
    if not matching or matching.get("decision") != "approved":
        return {
            "status": "error",
            "message": "No approved hpc_transfer decision matched the supplied approval reference",
            "approval_required": True,
            "gate": "hpc_transfer",
            "code": "transfer_gate_not_approved",
        }

    conditions = matching.get("conditions", {})
    if conditions.get("direction") not in (None, direction):
        return {"status": "error", "message": "Transfer direction does not match approval", "code": "transfer_approval_mismatch"}
    if conditions.get("remote_dir") not in (None, remote_dir):
        return {"status": "error", "message": "Remote directory does not match approval", "code": "transfer_approval_mismatch"}
    approved_paths = conditions.get("paths")
    if approved_paths is not None and sorted(approved_paths) != sorted(paths):
        return {"status": "error", "message": "Transfer paths do not match approval", "code": "transfer_approval_mismatch"}
    if conditions.get("target") != target:
        return {"status": "error", "message": "SSH target does not match approval", "code": "transfer_approval_mismatch"}
    approved_hash = conditions.get("transfer_request_hash")
    if approved_hash not in (None, fingerprint):
        return {"status": "error", "message": "Transfer request hash does not match approval", "code": "transfer_approval_mismatch"}

    gate = check_gate("hpc_transfer", {"project_root": project_root})
    if gate.get("status") != "pass":
        return {
            "status": "error",
            "message": "hpc_transfer gate is blocked by missing or failing evidence",
            "approval_required": True,
            "gate": "hpc_transfer",
            "code": "transfer_gate_blocked",
            "gate_result": gate,
        }
    return {"status": "success", "gate_decision_id": matching.get("decision_id"), "transfer_request_hash": fingerprint}


def _write_transfer_report(project_root: str, report: dict, params: dict) -> tuple[str, dict]:
    transfer_id = report["transfer_id"]
    root = Path(project_root).resolve()
    report_path = root / ".simflow" / "reports" / "compute" / "transfers" / f"{transfer_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact = register_artifact(
        report_path.name,
        "transfer_manifest",
        "computation",
        project_root=str(root),
        path=str(report_path.relative_to(root)),
        parent_artifacts=report.get("parent_artifacts", []),
        parameters={
            "direction": report["direction"],
            "remote_dir": report["remote_dir"],
            "transfer_id": transfer_id,
        },
        software="SimFlow hpc transfer",
        metadata={
            "evidence_keys": ["transfer_manifest"],
            "transfer_status": report["status"],
            "target_schema": report.get("target_schema"),
            "target": report.get("target"),
            "gate_decision_id": report.get("gate_decision_id"),
        },
    )
    return str(report_path.relative_to(root)), artifact


def _handle_transfer(params: dict, direction: str) -> dict:
    project_root = params.get("project_root")
    local_dir = params.get("local_dir")
    remote_dir = params.get("remote_dir")
    paths = params.get("paths")
    scheduler = params.get("scheduler", "ssh")
    target = params.get("target")
    if not project_root or not local_dir or not remote_dir or not isinstance(paths, list) or not paths:
        return {"status": "error", "message": "project_root, local_dir, remote_dir and non-empty paths are required"}
    if scheduler != "ssh":
        return {"status": "error", "message": "Transfers require scheduler='ssh'", "code": "ssh_scheduler_required"}

    try:
        target = normalize_target(target)
        remote_dir = validate_remote_dir(remote_dir)
        local_root = resolve_project_path(project_root, local_dir, "local_dir")
        safe_paths = sorted({str(path) for path in paths})
        # Validate all paths before any external command is started.
        from transfer import _safe_relative
        safe_paths = sorted({_safe_relative(path) for path in safe_paths})
    except TransferValidationError as exc:
        return {"status": "error", "message": str(exc), "code": "transfer_validation_error"}

    connector = _get_connector("ssh", target)
    if connector is None:
        return {"status": "error", "message": "SSH connector is unavailable"}

    approval = _transfer_decision(params, direction, remote_dir, safe_paths, target)
    if approval["status"] != "success":
        return approval

    transfer_id = f"transfer_{uuid.uuid4().hex[:12]}"
    report = {
        "transfer_id": transfer_id,
        "direction": direction,
        "status": "blocked",
        "project_root": str(Path(project_root).resolve()),
        "local_dir": str(local_root.relative_to(Path(project_root).resolve())),
        "remote_dir": remote_dir,
        "paths_requested": safe_paths,
        "target_schema": "ssh-target-v2",
        "target": target,
        "gate_decision_id": approval.get("gate_decision_id"),
        "transfer_request_hash": approval.get("transfer_request_hash"),
        "parent_artifacts": params.get("parent_artifacts", []),
    }
    try:
        if direction == "upload":
            local_files = expand_local_paths(local_root, safe_paths)
            if not local_files:
                raise TransferValidationError("transfer paths contain no regular files")
            expected = file_manifest(local_files)
            report["source_manifest"] = expected
            report["restricted_files"] = restricted_transfer_files(expected)
            result = connector.upload_files(str(local_root), remote_dir, [rel for rel, _ in local_files])
            report["transport"] = result
            if result.get("status") != "success":
                report["status"] = "failed"
            else:
                remote_result = connector.remote_file_manifest(remote_dir, [rel for rel, _ in local_files])
                report["remote_manifest"] = remote_result.get("manifest")
                if remote_result.get("status") != "success" or not manifests_match(expected, remote_result["manifest"]):
                    report["status"] = "blocked"
                    report["error"] = "Remote manifest does not match local manifest"
                else:
                    report["status"] = "verified"
        else:
            listing = connector.list_remote_files(remote_dir, safe_paths)
            if listing.get("status") != "success":
                report["status"] = "failed"
                report["transport"] = listing
            else:
                remote_files = listing["files"]
                if not remote_files:
                    raise TransferValidationError("remote transfer paths contain no regular files")
                before = connector.remote_file_manifest(remote_dir, remote_files)
                if before.get("status") != "success":
                    report["status"] = "failed"
                    report["transport"] = before
                else:
                    report["source_manifest"] = before["manifest"]
                    report["restricted_files"] = restricted_transfer_files(before["manifest"])
                    result = connector.download_files(remote_dir, str(local_root), remote_files)
                    report["transport"] = result
                    local_files = [(rel, local_root / rel) for rel in remote_files]
                    if result.get("status") != "success":
                        report["status"] = "failed"
                    else:
                        actual = file_manifest(local_files)
                        report["local_manifest"] = actual
                        report["status"] = "verified" if manifests_match(before["manifest"], actual) else "blocked"
                        if report["status"] == "blocked":
                            report["error"] = "Downloaded manifest does not match remote manifest"
    except (TransferValidationError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["error"] = str(exc)

    report_path, artifact = _write_transfer_report(project_root, report, params)
    return {
        "status": "success" if report["status"] == "verified" else "error",
        "data": {
            "transfer_id": transfer_id,
            "transfer_status": report["status"],
            "manifest_path": report_path,
            "artifact_id": artifact["artifact_id"],
            "report": report,
        },
    }


def handle_upload(params: dict) -> dict:
    return _handle_transfer(params, "upload")


def handle_download(params: dict) -> dict:
    return _handle_transfer(params, "download")


TOOLS = {
    "dry_run": handle_dry_run,
    "prepare": handle_prepare,
    "status": handle_status,
    "submit": handle_submit,
    "upload": handle_upload,
    "download": handle_download,
}

TOOL_DESCRIPTIONS = {
    "dry_run": "Validate an HPC job script without submitting it.",
    "prepare": "Prepare a scheduler job script for review.",
    "status": "Check scheduler job status through safe connector abstractions.",
    "submit": "Submit a job only when SimFlow approval and safety gates allow it.",
    "upload": "Upload approved files to an SSH HPC host and verify SHA-256 manifests.",
    "download": "Download approved files from an SSH HPC host and verify SHA-256 manifests.",
}

SSH_TARGET_SCHEMA = {
    "type": "object",
    "required": ["host"],
    "properties": {
        "host": {"type": "string", "minLength": 1, "maxLength": 253},
        "user": {"type": "string", "minLength": 1, "maxLength": 32},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
    },
    "additionalProperties": False,
}

TOOL_SCHEMAS = {
    "dry_run": {
        "type": "object",
        "required": ["script_path"],
        "properties": {
            "script_path": {"type": "string"},
            "manifest_path": {"type": "string"},
            "base_dir": {"type": "string"},
            "scheduler": {"type": "string"},
            "target": SSH_TARGET_SCHEMA,
        },
        "additionalProperties": False,
    },
    "prepare": {
        "type": "object",
        "properties": {
            "job_name": {"type": "string"},
            "executable": {"type": "string"},
            "nodes": {"type": "integer"},
            "ntasks": {"type": "integer"},
            "walltime": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "status": {
        "type": "object",
        "required": ["job_id"],
        "properties": {
            "job_id": {"type": "string"},
            "scheduler": {"type": "string"},
            "target": SSH_TARGET_SCHEMA,
        },
        "additionalProperties": False,
    },
    "submit": {
        "type": "object",
        "required": ["project_root", "script_path", "dry_run_evidence", "script_hash", "input_artifact_hash"],
        "properties": {
            "project_root": {"type": "string"},
            "script_path": {"type": "string"},
            "scheduler": {"type": "string"},
            "approval_token": {"type": "string"},
            "gate_decision_id": {"type": "string"},
            "dry_run_evidence": {"type": "string"},
            "script_hash": {"type": "string"},
            "input_artifact_hash": {"type": "string"},
            "timeout": {"type": "integer"},
            "transfer_manifest": {"type": "string"},
            "remote_workdir": {"type": "string"},
            "target": SSH_TARGET_SCHEMA,
        },
        "additionalProperties": False,
    },
    "upload": {
        "type": "object",
        "required": ["project_root", "local_dir", "remote_dir", "paths", "target"],
        "properties": {
            "project_root": {"type": "string"},
            "local_dir": {"type": "string"},
            "remote_dir": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "scheduler": {"type": "string", "enum": ["ssh"]},
            "approval_token": {"type": "string"},
            "gate_decision_id": {"type": "string"},
            "parent_artifacts": {"type": "array", "items": {"type": "string"}},
            "target": SSH_TARGET_SCHEMA,
        },
        "additionalProperties": False,
    },
    "download": {
        "type": "object",
        "required": ["project_root", "local_dir", "remote_dir", "paths", "target"],
        "properties": {
            "project_root": {"type": "string"},
            "local_dir": {"type": "string"},
            "remote_dir": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "scheduler": {"type": "string", "enum": ["ssh"]},
            "approval_token": {"type": "string"},
            "gate_decision_id": {"type": "string"},
            "parent_artifacts": {"type": "array", "items": {"type": "string"}},
            "target": SSH_TARGET_SCHEMA,
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    """Dispatch a request to the appropriate tool handler."""
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    from mcp.shared.stdio_server import run_mcp_server

    run_mcp_server("hpc", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
