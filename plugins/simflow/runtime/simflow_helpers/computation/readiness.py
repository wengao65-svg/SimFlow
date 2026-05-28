"""Build computation readiness evidence before any real submit."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    ("password_assignment", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+")),
    ("token_assignment", re.compile(r"(?i)\b(token|api[_-]?key|secret)\s*[:=]\s*\S+")),
    ("private_key_header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    """Return a SHA256 hex digest for a file."""
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def _relative_path(project_root: Path, path: str | Path) -> str:
    resolved = _resolve_project_path(project_root, path).resolve()
    try:
        return str(resolved.relative_to(project_root.resolve()))
    except ValueError:
        return str(resolved)


def _input_file_entries(input_manifest: dict[str, Any]) -> list[str]:
    entries: list[str] = []
    for key in ("generated_files", "input_files"):
        for value in input_manifest.get(key, []) or []:
            if isinstance(value, str):
                entries.append(value)
            elif isinstance(value, dict) and value.get("path"):
                entries.append(str(value["path"]))
    for value in input_manifest.get("files", []) or []:
        if isinstance(value, str):
            entries.append(value)
        elif isinstance(value, dict) and value.get("path"):
            entries.append(str(value["path"]))
    return list(dict.fromkeys(entries))


def build_input_validation(project_root: str | Path, input_manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate that generated input files exist and are non-empty."""
    root = Path(project_root).resolve()
    files = []
    missing_required = []
    empty_required = []
    for rel_path in _input_file_entries(input_manifest):
        full_path = _resolve_project_path(root, rel_path)
        exists = full_path.is_file()
        size = full_path.stat().st_size if exists else 0
        non_empty = exists and size > 0
        entry = {
            "path": rel_path,
            "exists": exists,
            "non_empty": non_empty,
            "size_bytes": size,
            "sha256": sha256_file(full_path) if exists else None,
        }
        files.append(entry)
        if not exists:
            missing_required.append(rel_path)
        elif not non_empty:
            empty_required.append(rel_path)

    status = "pass" if not missing_required and not empty_required else "fail"
    return {
        "generated_at": now_iso(),
        "status": status,
        "missing_required_files": missing_required,
        "empty_required_files": empty_required,
        "files": files,
    }


def build_resource_estimate(resources: dict[str, Any], scheduler: str) -> dict[str, Any]:
    """Normalize resource estimate evidence for gate evaluation."""
    warnings = []
    nodes = int(resources.get("recommended_nodes") or 1)
    ntasks = int(resources.get("recommended_ntasks") or 1)
    memory_gb = float(resources.get("recommended_memory_gb") or 0)
    walltime_hours = float(resources.get("estimated_walltime_hours") or 0)
    if nodes > 64:
        warnings.append({"code": "large_node_count", "value": nodes})
    if ntasks > 2048:
        warnings.append({"code": "large_task_count", "value": ntasks})
    if memory_gb > 500:
        warnings.append({"code": "large_memory_request", "value_gb": memory_gb})
    if walltime_hours > 168:
        warnings.append({"code": "long_walltime_request", "value_hours": walltime_hours})
    return {
        "generated_at": now_iso(),
        "status": "warning" if warnings else "pass",
        "scheduler": scheduler,
        "resources": resources,
        "warnings": warnings,
    }


def scan_credentials(project_root: str | Path, paths: list[str | Path]) -> dict[str, Any]:
    """Scan text files for credential-like patterns without storing values."""
    root = Path(project_root).resolve()
    findings = []
    for value in paths:
        path = _resolve_project_path(root, value)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern_id, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "path": _relative_path(root, path),
                        "line": line_no,
                        "pattern": pattern_id,
                    })
    return {
        "generated_at": now_iso(),
        "status": "pass" if not findings else "fail",
        "findings": findings,
        "scanned_paths": [_relative_path(root, path) for path in paths],
    }


def _overall_status(*statuses: str) -> str:
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "warning" for status in statuses):
        return "warning"
    return "pass"


def build_computation_readiness(
    *,
    project_root: str | Path,
    software: str,
    task: str,
    scheduler: str,
    input_manifest: dict[str, Any],
    input_manifest_path: str | Path,
    job_script_path: str | Path,
    resource_estimate: dict[str, Any],
    compute_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build all evidence required before hpc_submit approval."""
    root = Path(project_root).resolve()
    script_hash = sha256_file(job_script_path)
    input_hash = sha256_file(input_manifest_path)
    input_validation = build_input_validation(root, input_manifest)
    resource_report = build_resource_estimate(resource_estimate, scheduler)
    credential_scan = scan_credentials(
        root,
        [
            job_script_path,
            *_input_file_entries(input_manifest),
        ],
    )
    status = _overall_status(
        input_validation["status"],
        resource_report["status"],
        credential_scan["status"],
    )
    calculation_manifest = {
        "generated_at": now_iso(),
        "status": status,
        "software": software,
        "task": task,
        "scheduler": scheduler,
        "input_manifest_path": _relative_path(root, input_manifest_path),
        "input_manifest_hash": input_hash,
        "job_script": _relative_path(root, job_script_path),
        "job_script_hash": script_hash,
        "compute_plan": compute_plan,
    }
    dry_run_report = {
        "generated_at": now_iso(),
        "dry_run": True,
        "status": status,
        "software": software,
        "task": task,
        "scheduler": scheduler,
        "job_script": _relative_path(root, job_script_path),
        "script_hash": script_hash,
        "input_artifact_hash": input_hash,
        "input_manifest_hash": input_hash,
        "input_validation_status": input_validation["status"],
        "resource_estimate_status": resource_report["status"],
        "credential_scan_status": credential_scan["status"],
        "approval_required": True,
        "real_submit": False,
    }
    submit_readiness = {
        "project_root": str(root),
        "script_path": _relative_path(root, job_script_path),
        "scheduler": scheduler,
        "dry_run_evidence": "compute/dry_run_report.json",
        "script_hash": script_hash,
        "input_artifact_hash": input_hash,
        "approval_required": True,
    }
    return {
        "status": status,
        "calculation_manifest": calculation_manifest,
        "input_validation": input_validation,
        "resource_estimate": resource_report,
        "credential_scan": credential_scan,
        "dry_run_report": dry_run_report,
        "submit_readiness": submit_readiness,
    }


def write_readiness_evidence(project_root: str | Path, readiness: dict[str, Any]) -> dict[str, str]:
    """Write canonical computation readiness evidence under `.simflow/artifacts`."""
    root = Path(project_root).resolve()
    compute_dir = root / ".simflow" / "artifacts" / "compute"
    security_dir = root / ".simflow" / "artifacts" / "security"
    compute_dir.mkdir(parents=True, exist_ok=True)
    security_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "calculation_manifest": compute_dir / "calculation_manifest.json",
        "input_validation": compute_dir / "input_validation.json",
        "resource_estimate": compute_dir / "resource_estimate.json",
        "dry_run_report": compute_dir / "dry_run_report.json",
        "credential_scan": security_dir / "credential_scan.json",
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(readiness[key], indent=2, ensure_ascii=False), encoding="utf-8")
    return {key: _relative_path(root, path) for key, path in outputs.items()}
