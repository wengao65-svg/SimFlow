"""HPC MCP server with immutable planning and approval-bound execution."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from broker import SSHBrokerClient
from connectors.local import LocalConnector
from connectors.pbs import PBSConnector
from connectors.slurm import SlurmConnector
from mcp.shared.transport import dispatch_request
from run_plan import (
    RunPlanError,
    build_run_plan,
    load_run_plan,
    prepare_script,
    validate_run_plan_current,
)
from runtime.simflow_core.gates import get_gate_decisions
from runtime.simflow_core.records import record_event
from runtime.simflow_core.run_bindings import (
    bind_run_plan,
    find_job_run_plan_hash,
    get_run_plan_binding,
    latest_job_status,
)
from runtime.simflow_helpers.computation.job_records import record_submit_job
from transfer import (
    TransferValidationError,
    expand_local_paths,
    file_manifest,
    manifests_match,
    normalize_target,
    restricted_transfer_files,
    resolve_project_path,
)


_CONNECTORS = {
    "slurm": SlurmConnector,
    "pbs": PBSConnector,
    "local": LocalConnector,
    "ssh": SSHBrokerClient,
}


def _get_connector(scheduler: str = "auto", target: dict | None = None):
    """Return a bounded connector without inferring remote SSH credentials."""
    if target is not None:
        normalized = normalize_target(target)
        if scheduler not in ("auto", "ssh"):
            return None
        return SSHBrokerClient(**normalized)
    if scheduler == "auto":
        import os

        if os.environ.get("SIMFLOW_SLURM_HOST"):
            return SlurmConnector()
        return LocalConnector()
    if scheduler == "ssh":
        return None
    connector = _CONNECTORS.get(scheduler)
    if connector is None:
        return None
    try:
        return connector()
    except Exception:
        return None


def _connector_scheduler(connector) -> str:
    if isinstance(connector, SSHBrokerClient):
        return "ssh"
    if isinstance(connector, SlurmConnector):
        return "slurm"
    if isinstance(connector, PBSConnector):
        return "pbs"
    return "local"


def _error(message: str, code: str, **extra) -> dict:
    result = {"status": "error", "message": message, "code": code}
    result.update(extra)
    return result


def _approval_error(message: str, run_plan_hash: str, code: str = "approval_required") -> dict:
    return _error(
        message,
        code,
        approval_required=True,
        gate="hpc_submit",
        run_plan_hash=run_plan_hash,
    )


def _find_run_plan_approval(
    *,
    project_root: str,
    run_plan_hash: str,
    reference: str | None,
    allowed_gates: tuple[str, ...],
) -> dict:
    if not reference:
        return _approval_error(
            "An approval reference bound to run_plan_hash is required.",
            run_plan_hash,
        )
    for gate_name in allowed_gates:
        for decision in get_gate_decisions(gate_name, project_root=project_root):
            conditions = decision.get("conditions") if isinstance(decision.get("conditions"), dict) else {}
            matches_reference = (
                decision.get("decision_id") == reference
                or decision.get("approval_token") == reference
                or conditions.get("approval_token") == reference
            )
            if not matches_reference:
                continue
            if decision.get("decision") != "approved":
                return _approval_error("The matching approval decision is not approved.", run_plan_hash)
            approved_hash = conditions.get("run_plan_hash")
            if approved_hash != run_plan_hash:
                return _approval_error(
                    "The approval is bound to a different immutable run plan.",
                    run_plan_hash,
                    code="run_plan_approval_mismatch",
                )
            return {
                "status": "success",
                "gate": gate_name,
                "gate_decision_id": decision.get("decision_id"),
                "run_plan_hash": run_plan_hash,
            }
    return _approval_error(
        "No approved gate decision matched the supplied approval reference.",
        run_plan_hash,
        code="run_plan_not_approved",
    )


def handle_plan(params: dict) -> dict:
    """Prepare or inspect a script, validate inputs, and persist one run plan."""
    project_root = params.get("project_root")
    if not project_root:
        return _error("project_root is required", "project_root_required")
    try:
        script, generated = prepare_script(project_root, params)
        requested_scheduler = str(params.get("scheduler", "auto")).lower()
        connector = _get_connector(requested_scheduler, params.get("target"))
        if connector is None:
            return _error(f"Unknown or incomplete scheduler target: {requested_scheduler}", "unknown_scheduler")
        plan_params = dict(params)
        plan_params["scheduler"] = _connector_scheduler(connector)
        validation = connector.dry_run(
            str(script),
            params.get("manifest_path", ""),
            params.get("base_dir", project_root),
        )
        plan = build_run_plan(
            project_root,
            plan_params,
            script=script,
            script_generated=generated,
            validation=validation,
        )
        binding = bind_run_plan(
            project_root,
            run_plan_hash=plan["run_plan_hash"],
            plan_path=plan["plan_path"],
            scheduler=plan["scheduler"],
            script_path=plan["script"]["path"],
            submit_ready=plan["submit_ready"],
            experiment_id=params.get("experiment_id"),
            attempt_id=params.get("attempt_id"),
        )
    except (RunPlanError, TransferValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _error(str(exc), "run_plan_invalid")
    status = "success" if plan["submit_ready"] else "error"
    return {
        "status": status,
        "data": plan,
        "binding": binding,
        "approval_required": plan["submit_ready"],
        "gate": "hpc_submit" if plan["submit_ready"] else None,
    }


def _normalized_status(result: dict) -> str | None:
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    raw = str(data.get("state") or data.get("status") or result.get("status") or "").upper()
    if raw in {"PENDING", "CONFIGURING", "QUEUED", "Q", "HELD"}:
        return "queued"
    if raw in {"RUNNING", "R", "COMPLETING", "EXITING"}:
        return "running"
    if raw in {"COMPLETED", "C", "SUCCESS"}:
        return "completed"
    if raw in {"FAILED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY", "ERROR"}:
        return "failed"
    if raw in {"CANCELLED", "CANCELED"}:
        return "cancelled"
    return None


def handle_status(params: dict) -> dict:
    """Check a local, scheduler, or broker-backed job status."""
    job_id = params.get("job_id", "")
    scheduler = params.get("scheduler", "auto")
    if not job_id:
        return _error("job_id is required", "job_id_required")
    if scheduler == "ssh" and not params.get("target"):
        return _error("target is required for SSH status", "target_required")
    try:
        connector = _get_connector(scheduler, params.get("target"))
    except TransferValidationError as exc:
        return _error(str(exc), "invalid_target")
    if connector is None:
        return _error(f"Unknown scheduler: {scheduler}", "unknown_scheduler")
    result = connector.status(str(job_id))
    project_root = params.get("project_root")
    if not project_root or result.get("status") == "error":
        return result
    recorded_hash = find_job_run_plan_hash(project_root, str(job_id))
    requested_hash = params.get("run_plan_hash")
    if requested_hash and recorded_hash and requested_hash != recorded_hash:
        return _error(
            "job_id is recorded against a different immutable run plan",
            "job_run_plan_mismatch",
            job_id=str(job_id),
            recorded_run_plan_hash=recorded_hash,
        )
    run_plan_hash = recorded_hash
    normalized = _normalized_status(result)
    if not run_plan_hash or not normalized:
        result["recorded_transition"] = False
        if requested_hash and not recorded_hash:
            result["recording_reason"] = "job_id has no recorded submit for this project"
        return result
    if latest_job_status(project_root, str(job_id)) == normalized:
        result["recorded_transition"] = False
        return result
    binding = get_run_plan_binding(project_root, run_plan_hash) or {}
    record = record_event(
        project_root,
        kind="run",
        summary=f"Scheduler job {job_id} is {normalized}",
        status=normalized,
        stage="computation",
        run_id=binding.get("attempt_id") or f"{scheduler}_{job_id}",
        experiment_id=binding.get("experiment_id"),
        attempt_id=binding.get("attempt_id"),
        details={
            "operation": "status",
            "job_id": str(job_id),
            "scheduler": scheduler,
            "run_plan_hash": run_plan_hash,
            "raw_status": result,
        },
    )
    result["recorded_transition"] = True
    result["run_record_id"] = record["record_id"]
    result["binding"] = binding
    return result


def _transfer_report_path(project_root: str, transfer_id: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    return root / ".simflow" / "reports" / "hpc" / "transfers" / f"{transfer_id}.json"


def _record_transfer(project_root: str, report: dict) -> dict:
    root = Path(project_root).expanduser().resolve()
    path = _transfer_report_path(project_root, report["transfer_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    binding = get_run_plan_binding(str(root), report["run_plan_hash"]) or {}
    record = record_event(
        str(root),
        kind="run",
        summary=f"HPC {report['direction']} {report['status']}",
        status="completed" if report["status"] == "verified" else "failed",
        stage="computation",
        run_id=report["transfer_id"],
        experiment_id=binding.get("experiment_id"),
        attempt_id=binding.get("attempt_id"),
        artifacts=[{
            "path": str(path.relative_to(root)),
            "role": "transfer_report",
        }],
        details={
            "operation": "transfer",
            "direction": report["direction"],
            "run_plan_hash": report["run_plan_hash"],
            "gate_decision_id": report.get("gate_decision_id"),
            "target": report.get("target"),
            "remote_dir": report.get("remote_dir"),
            "source_manifest_sha256": (report.get("source_manifest") or {}).get("manifest_sha256"),
            "restricted_files": report.get("restricted_files", []),
            "error": report.get("error"),
            "experiment_id": binding.get("experiment_id"),
            "attempt_id": binding.get("attempt_id"),
        },
    )
    return {"path": str(path.relative_to(root)), "record": record}


def handle_transfer(params: dict) -> dict:
    """Execute the transfer declared by an approved immutable run plan."""
    project_root = params.get("project_root")
    run_plan_hash = params.get("run_plan_hash")
    direction = params.get("direction")
    if not project_root or not run_plan_hash or direction not in {"upload", "download"}:
        return _error(
            "project_root, run_plan_hash, and direction=upload|download are required",
            "transfer_params_required",
        )
    try:
        plan = validate_run_plan_current(project_root, run_plan_hash)
    except (RunPlanError, TransferValidationError, OSError, ValueError) as exc:
        return _error(str(exc), "run_plan_stale", approval_required=True, run_plan_hash=run_plan_hash)
    transfer = plan.get("transfer")
    if not isinstance(transfer, dict) or transfer.get("direction") != direction:
        return _error("direction does not match the immutable run plan", "run_plan_transfer_mismatch")
    target = plan.get("target")
    if not target:
        return _error("run plan does not declare an SSH target", "target_required")
    approval = _find_run_plan_approval(
        project_root=project_root,
        run_plan_hash=run_plan_hash,
        reference=params.get("gate_decision_id") or params.get("approval_token"),
        allowed_gates=("hpc_submit", "hpc_transfer"),
    )
    if approval["status"] != "success":
        return approval
    try:
        local_root = resolve_project_path(project_root, transfer["local_dir"], "transfer.local_dir")
        connector = _get_connector("ssh", target)
    except TransferValidationError as exc:
        return _error(str(exc), "transfer_validation_error")
    if connector is None:
        return _error("SSH connector is unavailable", "hpc_broker_unavailable")

    transfer_id = f"transfer_{uuid.uuid4().hex[:12]}"
    report = {
        "transfer_id": transfer_id,
        "direction": direction,
        "status": "failed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_plan_hash": run_plan_hash,
        "local_dir": str(local_root.relative_to(Path(project_root).resolve())),
        "remote_dir": transfer["remote_dir"],
        "paths_requested": transfer["paths"],
        "target_schema": "ssh-target-v2",
        "target": target,
        "gate_decision_id": approval["gate_decision_id"],
        "destructive_scope": plan.get("destructive_scope", []),
    }
    try:
        if direction == "upload":
            local_files = expand_local_paths(local_root, transfer["paths"])
            if not local_files:
                raise TransferValidationError("transfer paths contain no regular files")
            expected = file_manifest(local_files)
            report["source_manifest"] = expected
            report["restricted_files"] = restricted_transfer_files(expected)
            result = connector.upload_files(str(local_root), transfer["remote_dir"], [rel for rel, _ in local_files])
            report["transport"] = result
            if result.get("status") == "success":
                remote_result = connector.remote_file_manifest(
                    transfer["remote_dir"], [rel for rel, _ in local_files]
                )
                report["remote_manifest"] = remote_result.get("manifest")
                if remote_result.get("status") == "success" and manifests_match(expected, remote_result["manifest"]):
                    report["status"] = "verified"
                else:
                    report["error"] = "Remote manifest does not match local manifest"
            else:
                report["error"] = result.get("message") or "upload failed"
        else:
            listing = connector.list_remote_files(transfer["remote_dir"], transfer["paths"])
            report["transport"] = listing
            if listing.get("status") == "success" and listing.get("files"):
                remote_files = listing["files"]
                before = connector.remote_file_manifest(transfer["remote_dir"], remote_files)
                if before.get("status") == "success":
                    report["source_manifest"] = before["manifest"]
                    report["restricted_files"] = restricted_transfer_files(before["manifest"])
                    result = connector.download_files(transfer["remote_dir"], str(local_root), remote_files)
                    report["transport"] = result
                    if result.get("status") == "success":
                        actual = file_manifest([(rel, local_root / rel) for rel in remote_files])
                        report["local_manifest"] = actual
                        if manifests_match(before["manifest"], actual):
                            report["status"] = "verified"
                        else:
                            report["error"] = "Downloaded manifest does not match remote manifest"
                    else:
                        report["error"] = result.get("message") or "download failed"
                else:
                    report["error"] = before.get("message") or "remote manifest failed"
            else:
                report["error"] = listing.get("message") or "remote transfer paths contain no regular files"
    except (TransferValidationError, OSError, ValueError) as exc:
        report["error"] = str(exc)

    recorded = _record_transfer(project_root, report)
    return {
        "status": "success" if report["status"] == "verified" else "error",
        "data": {
            "transfer_id": transfer_id,
            "transfer_status": report["status"],
            "manifest_path": recorded["path"],
            "run_record_id": recorded["record"]["record_id"],
            "report": report,
        },
    }


def handle_submit(params: dict) -> dict:
    """Submit an approved immutable run plan without accepting mutable bindings."""
    project_root = params.get("project_root")
    run_plan_hash = params.get("run_plan_hash")
    if not project_root or not run_plan_hash:
        return _error("project_root and run_plan_hash are required", "submit_params_required")
    try:
        plan = validate_run_plan_current(project_root, run_plan_hash)
    except (RunPlanError, TransferValidationError, OSError, ValueError) as exc:
        return _error(str(exc), "run_plan_stale", approval_required=True, run_plan_hash=run_plan_hash)
    approval = _find_run_plan_approval(
        project_root=project_root,
        run_plan_hash=run_plan_hash,
        reference=params.get("gate_decision_id") or params.get("approval_token"),
        allowed_gates=("hpc_submit",),
    )
    if approval["status"] != "success":
        return approval
    scheduler = plan["scheduler"]
    binding = get_run_plan_binding(project_root, run_plan_hash) or {}
    target = plan.get("target")
    connector = _get_connector(scheduler, target)
    if connector is None:
        return _error(f"Unknown or incomplete scheduler target: {scheduler}", "unknown_scheduler")
    script_path = str(Path(project_root).resolve() / plan["script"]["path"])
    submit_kwargs = {
        "project_root": project_root,
        "run_plan_hash": run_plan_hash,
        "approval_token": params.get("approval_token"),
        "gate_decision_id": approval["gate_decision_id"],
    }
    if isinstance(connector, SSHBrokerClient):
        if not params.get("transfer_manifest"):
            return _error(
                "SSH submit requires a verified transfer manifest from hpc/transfer",
                "transfer_manifest_required",
            )
        submit_kwargs.update({
            "transfer_manifest": params["transfer_manifest"],
            "remote_workdir": plan.get("remote_workdir"),
            "target": target,
        })
    if scheduler == "local":
        submit_kwargs["timeout"] = params.get("timeout", 3600)
    result = connector.submit(script_path, **submit_kwargs)

    succeeded = result.get("status") == "success" or result.get("success") is True
    job_id = result.get("job_id")
    if succeeded and not job_id:
        job_id = f"local_{run_plan_hash[:12]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        result["job_id"] = job_id
    record = record_submit_job(
        project_root=project_root,
        scheduler=result.get("scheduler") or scheduler,
        job_id=str(job_id or f"submit_{uuid.uuid4().hex[:12]}"),
        status=("completed" if scheduler == "local" and succeeded else "submitted" if succeeded else "failed"),
        script_path=plan["script"]["path"],
        gate_decision_id=approval["gate_decision_id"],
        run_plan_hash=run_plan_hash,
        submit_result=result,
        experiment_id=binding.get("experiment_id"),
        attempt_id=binding.get("attempt_id"),
    )
    result["run_record_id"] = record["record"]["record_id"]
    return result


TOOLS = {
    "plan": handle_plan,
    "transfer": handle_transfer,
    "submit": handle_submit,
    "status": handle_status,
}

TOOL_DESCRIPTIONS = {
    "plan": "Prepare or validate a job and persist an immutable approval-bound run plan.",
    "transfer": "Execute the upload or download declared by an approved run plan and verify manifests.",
    "submit": "Submit an unchanged approved run plan to local, scheduler, or broker-backed execution.",
    "status": "Check job status through bounded connector abstractions.",
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
    "plan": {
        "type": "object",
        "required": ["project_root", "script_path", "input_paths"],
        "properties": {
            "project_root": {"type": "string"},
            "script_path": {"type": "string"},
            "input_paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "scheduler": {"type": "string", "enum": ["auto", "local", "slurm", "pbs", "ssh"]},
            "target": SSH_TARGET_SCHEMA,
            "remote_workdir": {"type": "string"},
            "manifest_path": {"type": "string"},
            "base_dir": {"type": "string"},
            "resources": {"type": "object"},
            "destructive_scope": {"type": "array", "items": {"type": "string"}},
            "experiment_id": {"type": "string"},
            "attempt_id": {"type": "string"},
            "generate": {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "executable": {"type": "string"},
                    "nodes": {"type": "integer", "minimum": 1},
                    "ntasks": {"type": "integer", "minimum": 1},
                    "walltime": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "transfer": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["upload", "download"]},
                    "local_dir": {"type": "string"},
                    "remote_dir": {"type": "string"},
                    "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    },
    "transfer": {
        "type": "object",
        "required": ["project_root", "run_plan_hash", "direction"],
        "properties": {
            "project_root": {"type": "string"},
            "run_plan_hash": {"type": "string"},
            "direction": {"type": "string", "enum": ["upload", "download"]},
            "approval_token": {"type": "string"},
            "gate_decision_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "submit": {
        "type": "object",
        "required": ["project_root", "run_plan_hash"],
        "properties": {
            "project_root": {"type": "string"},
            "run_plan_hash": {"type": "string"},
            "approval_token": {"type": "string"},
            "gate_decision_id": {"type": "string"},
            "timeout": {"type": "integer", "minimum": 1},
            "transfer_manifest": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "status": {
        "type": "object",
        "required": ["job_id"],
        "properties": {
            "job_id": {"type": "string"},
            "scheduler": {"type": "string", "enum": ["auto", "local", "slurm", "pbs", "ssh"]},
            "target": SSH_TARGET_SCHEMA,
            "project_root": {"type": "string"},
            "run_plan_hash": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    from mcp.shared.stdio_server import run_mcp_server

    run_mcp_server("hpc", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
