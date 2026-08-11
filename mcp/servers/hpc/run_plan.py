"""Immutable run-plan construction and validation for HPC operations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.simflow_core.hpc import generate_slurm_script
from runtime.simflow_core.records import sanitize_record_value
from runtime.simflow_core.state import resolve_project_root
from runtime.simflow_helpers.computation.readiness import scan_credentials

try:
    from transfer import (
        TransferValidationError,
        _safe_relative,
        expand_local_paths,
        file_manifest,
        normalize_target,
        restricted_transfer_files,
        validate_remote_dir,
    )
except ModuleNotFoundError:  # pragma: no cover - package import path
    from .transfer import (
        TransferValidationError,
        _safe_relative,
        expand_local_paths,
        file_manifest,
        normalize_target,
        restricted_transfer_files,
        validate_remote_dir,
    )


RUN_PLAN_SCHEMA = "simflow.hpc_run_plan.v1"
PLAN_DIR = Path(".simflow/reports/hpc/plans")
SUPPORTED_SCHEDULERS = {"auto", "local", "slurm", "pbs", "ssh"}


class RunPlanError(ValueError):
    """Raised when a run plan is incomplete, stale, or unsafe."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_file(root: Path, value: str, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RunPlanError(f"{field} must be a non-empty path")
    candidate = Path(value).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RunPlanError(f"{field} must remain inside project_root") from exc
    return resolved


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _normalized_resources(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise RunPlanError("resources must be an object")
    return sanitize_record_value(value)


def _normalized_scope(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise RunPlanError("destructive_scope must be an array of non-empty strings")
    return sorted(set(value))


def _validation_status(result: dict[str, Any]) -> str:
    value = result.get("status", result.get("overall"))
    if value in {"pass", "warning", "fail"}:
        return value
    if result.get("valid") is True or result.get("success") is True:
        return "pass"
    return "fail"


def prepare_script(project_root: str, params: dict[str, Any]) -> tuple[Path, bool]:
    """Resolve an existing script or create one from bounded SLURM fields."""
    root = resolve_project_root(project_root=project_root)
    script = _project_file(root, params.get("script_path", ""), "script_path")
    generate = params.get("generate")
    if generate is None:
        if not script.is_file():
            raise RunPlanError(f"Script not found: {_relative(root, script)}")
        return script, False
    if not isinstance(generate, dict):
        raise RunPlanError("generate must be an object")
    scheduler = params.get("scheduler", "auto")
    if scheduler not in {"auto", "slurm"}:
        raise RunPlanError("script generation currently supports scheduler='slurm' or 'auto'")
    content = generate_slurm_script(
        job_name=generate.get("job_name", "simflow_job"),
        executable=generate.get("executable", "vasp_std"),
        nodes=int(generate.get("nodes", 1)),
        ntasks=int(generate.get("ntasks", 16)),
        time=generate.get("walltime", "04:00:00"),
    )
    if script.exists():
        if not script.is_file() or script.read_text(encoding="utf-8") != content:
            raise RunPlanError("generated script would overwrite different existing content")
        return script, False
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(content, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o100)
    return script, True


def _build_identity(
    *,
    root: Path,
    script: Path,
    scheduler: str,
    target: dict[str, Any] | None,
    remote_workdir: str | None,
    input_paths: list[str],
    resources: dict[str, Any],
    transfer: dict[str, Any] | None,
    destructive_scope: list[str],
) -> dict[str, Any]:
    files = expand_local_paths(root, input_paths)
    if not files:
        raise RunPlanError("input_paths contain no regular files")
    manifest = file_manifest(files)
    restricted = restricted_transfer_files(manifest)
    transfer_identity = dict(transfer) if isinstance(transfer, dict) else None
    if transfer_identity and transfer_identity.get("direction") == "upload":
        local_root = _project_file(root, transfer_identity["local_dir"], "transfer.local_dir")
        transfer_files = expand_local_paths(local_root, transfer_identity["paths"])
        if not transfer_files:
            raise RunPlanError("transfer.paths contain no regular files")
        transfer_manifest = file_manifest(transfer_files)
        transfer_identity["source_manifest_sha256"] = transfer_manifest["manifest_sha256"]
        transfer_identity["file_count"] = transfer_manifest["file_count"]
        transfer_identity["total_size_bytes"] = transfer_manifest["total_size_bytes"]
        transfer_identity["files"] = transfer_manifest["files"]
        restricted_by_key = {
            (item["path"], item["sha256"]): item
            for item in [*restricted, *restricted_transfer_files(transfer_manifest)]
        }
        restricted = sorted(restricted_by_key.values(), key=lambda item: (item["path"], item["sha256"]))
    return {
        "schema_version": RUN_PLAN_SCHEMA,
        "scheduler": scheduler,
        "target": target,
        "remote_workdir": remote_workdir,
        "script": {
            "path": _relative(root, script),
            "sha256": _sha256_file(script),
            "size_bytes": script.stat().st_size,
        },
        "inputs": {
            "paths": sorted(input_paths),
            "manifest_sha256": manifest["manifest_sha256"],
            "file_count": manifest["file_count"],
            "total_size_bytes": manifest["total_size_bytes"],
            "files": manifest["files"],
        },
        "resources": resources,
        "transfer": transfer_identity,
        "destructive_scope": destructive_scope,
        "restricted_files": restricted,
    }


def build_run_plan(
    project_root: str,
    params: dict[str, Any],
    *,
    script: Path,
    script_generated: bool,
    validation: dict[str, Any],
) -> dict[str, Any]:
    """Create and persist one immutable run plan."""
    root = resolve_project_root(project_root=project_root)
    scheduler = str(params.get("scheduler", "auto")).lower()
    if scheduler not in SUPPORTED_SCHEDULERS:
        raise RunPlanError(f"Unsupported scheduler: {scheduler}")
    target = normalize_target(params.get("target")) if params.get("target") is not None else None
    if scheduler == "ssh" and target is None:
        raise RunPlanError("target is required for scheduler='ssh'")
    remote_workdir = params.get("remote_workdir")
    if remote_workdir is not None:
        remote_workdir = validate_remote_dir(remote_workdir)
    if scheduler == "ssh" and not remote_workdir:
        raise RunPlanError("remote_workdir is required for scheduler='ssh'")

    raw_inputs = params.get("input_paths")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise RunPlanError("input_paths must be a non-empty array")
    input_paths = sorted({_safe_relative(str(value), "input_paths") for value in raw_inputs})
    script_rel = _relative(root, script)
    if script_rel not in input_paths:
        input_paths.append(script_rel)
        input_paths.sort()

    transfer = None
    transfer_params = params.get("transfer")
    if transfer_params is not None or scheduler == "ssh":
        if transfer_params is None:
            transfer_params = {}
        if not isinstance(transfer_params, dict):
            raise RunPlanError("transfer must be an object")
        direction = transfer_params.get("direction", "upload")
        if direction not in {"upload", "download"}:
            raise RunPlanError("transfer.direction must be 'upload' or 'download'")
        local_dir_path = _project_file(root, transfer_params.get("local_dir", "."), "transfer.local_dir")
        try:
            local_dir = _relative(root, local_dir_path)
        except ValueError as exc:
            raise RunPlanError("transfer.local_dir must remain inside project_root") from exc
        local_dir = local_dir or "."
        raw_paths = transfer_params.get("paths") or input_paths
        if not isinstance(raw_paths, list) or not raw_paths:
            raise RunPlanError("transfer.paths must be a non-empty array")
        transfer_paths = sorted({_safe_relative(str(value), "transfer.paths") for value in raw_paths})
        transfer = {
            "direction": direction,
            "local_dir": local_dir,
            "remote_dir": validate_remote_dir(transfer_params.get("remote_dir") or remote_workdir or ""),
            "paths": transfer_paths,
        }

    resources = _normalized_resources(params.get("resources"))
    if params.get("generate") and not resources:
        generate = params["generate"]
        resources = {
            "nodes": int(generate.get("nodes", 1)),
            "ntasks": int(generate.get("ntasks", 16)),
            "walltime": generate.get("walltime", "04:00:00"),
        }
    destructive_scope = _normalized_scope(params.get("destructive_scope"))
    identity = _build_identity(
        root=root,
        script=script,
        scheduler=scheduler,
        target=target,
        remote_workdir=remote_workdir,
        input_paths=input_paths,
        resources=resources,
        transfer=transfer,
        destructive_scope=destructive_scope,
    )
    credential_paths = [
        item["path"]
        for item in identity["inputs"]["files"]
        if Path(item["path"]).name.upper() != "POTCAR"
    ]
    credential_scan = scan_credentials(root, credential_paths)
    validation_status = _validation_status(validation)
    status = "fail" if "fail" in {validation_status, credential_scan["status"]} else (
        "warning" if "warning" in {validation_status, credential_scan["status"]} else "pass"
    )
    run_plan_hash = _hash_payload(identity)
    plan = {
        **identity,
        "run_plan_hash": run_plan_hash,
        "status": status,
        "submit_ready": status in {"pass", "warning"},
        "generated_at": _now_iso(),
        "script_generated": script_generated,
        "validation": sanitize_record_value(validation),
        "credential_scan": credential_scan,
    }
    path = root / PLAN_DIR / f"{run_plan_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("run_plan_hash") != run_plan_hash:
            raise RunPlanError("existing run-plan file has inconsistent identity")
    else:
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    plan["plan_path"] = str(path.relative_to(root))
    return plan


def load_run_plan(project_root: str, run_plan_hash: str) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    if not isinstance(run_plan_hash, str) or len(run_plan_hash) != 64:
        raise RunPlanError("run_plan_hash must be a SHA-256 hex digest")
    try:
        int(run_plan_hash, 16)
    except ValueError as exc:
        raise RunPlanError("run_plan_hash must be a SHA-256 hex digest") from exc
    path = root / PLAN_DIR / f"{run_plan_hash}.json"
    if not path.is_file():
        raise RunPlanError("run plan was not found under project_root")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunPlanError("run plan is not valid JSON") from exc
    if plan.get("schema_version") != RUN_PLAN_SCHEMA or plan.get("run_plan_hash") != run_plan_hash:
        raise RunPlanError("run plan schema or hash is invalid")
    plan["plan_path"] = str(path.relative_to(root))
    return plan


def validate_run_plan_current(project_root: str, run_plan_hash: str) -> dict[str, Any]:
    """Recompute all local hashes and reject stale or modified plans."""
    root = resolve_project_root(project_root=project_root)
    plan = load_run_plan(str(root), run_plan_hash)
    script = _project_file(root, plan["script"]["path"], "plan.script.path")
    if not script.is_file():
        raise RunPlanError("planned job script is missing")
    identity = _build_identity(
        root=root,
        script=script,
        scheduler=plan["scheduler"],
        target=plan.get("target"),
        remote_workdir=plan.get("remote_workdir"),
        input_paths=plan["inputs"]["paths"],
        resources=plan.get("resources") or {},
        transfer=plan.get("transfer"),
        destructive_scope=plan.get("destructive_scope") or [],
    )
    current_hash = _hash_payload(identity)
    if current_hash != run_plan_hash:
        raise RunPlanError(
            "run plan is stale because script, inputs, target, resources, transfer scope, or restricted-file metadata changed"
        )
    if plan.get("status") not in {"pass", "warning"} or not plan.get("submit_ready"):
        raise RunPlanError("run plan did not pass validation")
    return plan
