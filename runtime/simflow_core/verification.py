"""Verification helpers for final delivery audit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .state import read_state, resolve_project_root

VERIFICATION_FILE = ".simflow/state/verification.json"
VERIFY_REPORT_JSON = ".simflow/reports/verify/verification_report.json"
VERIFY_REPORT_MARKDOWN = ".simflow/reports/verify/verification_report.md"
REPRODUCIBILITY_MANIFEST_FILE = ".simflow/reports/reproducibility/reproducibility_manifest.json"
FINAL_HANDOFF_FILE = ".simflow/reports/handoff/final_handoff.json"
REQUIRED_WRITING_OUTPUTS = {
    "methods.md": ".simflow/reports/writing/methods.md",
    "results.md": ".simflow/reports/writing/results.md",
    "reproducibility_package.md": ".simflow/reports/reproducibility/reproducibility_package.md",
    "final_handoff.md": ".simflow/reports/handoff/final_handoff.md",
    "final_handoff.json": ".simflow/reports/handoff/final_handoff.json",
}
REQUIRED_CHECK_NAMES = [
    "artifact_traceability",
    "required_writing_outputs",
    "reproducibility_manifest_present",
    "final_handoff_present",
    "compute_truth_declared",
    "no_real_submit_without_approval",
    "no_sensitive_paths",
    "checkpoint_summary_present",
]
SENSITIVE_KEY_PARTS = ("token", "password", "secret")
APPROVED_GATE_STATUSES = {"approve", "approved", "allow", "allowed", "pass", "passed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _normalize_status(status: str) -> str:
    normalized = (status or "").lower()
    if normalized not in {"pass", "warning", "fail", "pending"}:
        raise ValueError(f"Unsupported verification status: {status}")
    return normalized


def _report_path(project_root: Path, relative_path: str) -> Path:
    return project_root / relative_path


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _latest_artifact(
    artifacts: list[dict[str, Any]],
    *,
    name: str | None = None,
    stage: str | None = None,
) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if (name is None or artifact.get("name") == name)
        and (stage is None or artifact.get("stage") == stage)
    ]
    return matches[-1] if matches else None


def create_verification_report(
    stage: str,
    workflow_id: str,
    base_dir: str = ".",
    source_artifact_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "workflow_id": workflow_id,
        "status": "pending",
        "generated_at": _now_iso(),
        "completed_at": None,
        "checks": [],
        "warnings": [],
        "failures": [],
        "source_artifact_ids": _dedupe(list(source_artifact_ids or [])),
    }


def add_check(
    report: dict[str, Any],
    name: str,
    status: str,
    message: str = "",
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    check = {
        "name": name,
        "status": _normalize_status(status),
        "message": message,
        "details": details or {},
        "checked_at": _now_iso(),
    }
    report.setdefault("checks", []).append(check)
    return report


def _rollup_status(checks: list[dict[str, Any]]) -> str:
    overall = "pass"
    for check in checks:
        status = check.get("status")
        if status == "fail":
            return "fail"
        if status == "warning":
            overall = "warning"
    return overall


def _complete_report(report: dict[str, Any]) -> dict[str, Any]:
    warnings = list(report.get("warnings", []))
    failures = list(report.get("failures", []))
    for check in report.get("checks", []):
        if check.get("status") == "warning":
            warnings.append(check.get("message") or check.get("name") or "warning")
        if check.get("status") == "fail":
            failures.append(check.get("message") or check.get("name") or "failure")
    report["warnings"] = _dedupe(warnings)
    report["failures"] = _dedupe(failures)
    report["source_artifact_ids"] = _dedupe(list(report.get("source_artifact_ids", [])))
    report["status"] = _rollup_status(report.get("checks", []))
    report["completed_at"] = _now_iso()
    return report


def persist_verification_state(
    report: dict[str, Any],
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / VERIFICATION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = payload
            elif isinstance(payload, dict):
                reports = payload.get("reports")
                if isinstance(reports, list):
                    existing = reports
        except json.JSONDecodeError:
            existing = []
    existing.append(report)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Verification Report",
        "",
        f"- Stage: {report.get('stage', 'unknown')}",
        f"- Workflow ID: {report.get('workflow_id', 'unknown')}",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Generated at: {report.get('generated_at', 'unknown')}",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(f"- {check.get('name', 'unknown')}: {check.get('status', 'unknown')} — {check.get('message', '')}")
    lines.extend([
        "",
        "## Warnings",
        "",
    ])
    warning_items = report.get("warnings", []) or ["None"]
    lines.extend(f"- {item}" for item in warning_items)
    lines.extend([
        "",
        "## Failures",
        "",
    ])
    failure_items = report.get("failures", []) or ["None"]
    lines.extend(f"- {item}" for item in failure_items)
    lines.extend([
        "",
        "## Source artifact IDs",
        "",
    ])
    source_items = report.get("source_artifact_ids", []) or ["None"]
    lines.extend(f"- {item}" for item in source_items)
    return "\n".join(lines)


def write_verification_outputs(
    report: dict[str, Any],
    base_dir: str = ".",
    project_root: Optional[str] = None,
    write_markdown: bool = False,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    json_path = _report_path(root, VERIFY_REPORT_JSON)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["output_file"] = VERIFY_REPORT_JSON
    if write_markdown:
        markdown_path = _report_path(root, VERIFY_REPORT_MARKDOWN)
        markdown_path.write_text(_build_markdown(report), encoding="utf-8")
        report["markdown_file"] = VERIFY_REPORT_MARKDOWN
    return report


def finalize_report(
    report: dict[str, Any],
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict[str, Any]:
    completed = _complete_report(report)
    persist_verification_state(completed, base_dir=base_dir, project_root=project_root)
    return completed


def get_verifications(stage: Optional[str] = None, base_dir: str = ".", project_root: Optional[str] = None) -> list[dict[str, Any]]:
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / VERIFICATION_FILE
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    reports = payload if isinstance(payload, list) else payload.get("reports", []) if isinstance(payload, dict) else []
    if stage:
        return [report for report in reports if report.get("stage") == stage]
    return reports


def run_checks(
    stage: str,
    workflow_id: str,
    checks: list[tuple[str, Callable[[], dict[str, Any]]]],
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict[str, Any]:
    report = create_verification_report(stage, workflow_id, base_dir=base_dir)
    for name, check_fn in checks:
        try:
            result = check_fn()
            add_check(report, name, result.get("status", "fail"), result.get("message", ""), result.get("details"))
        except Exception as exc:
            add_check(report, name, status="fail", message=str(exc))
    return finalize_report(report, base_dir=base_dir, project_root=project_root)


def _is_redacted(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return lowered in {"<redacted>", "redacted"} or "redacted" in lowered


def _scan_sensitive_content(
    value: Any,
    field_path: str,
    warnings: list[str],
    failures: list[str],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            current_path = f"{field_path}.{key}" if field_path else key
            lowered_key = key.lower()
            if any(part in lowered_key for part in SENSITIVE_KEY_PARTS):
                if _is_redacted(item):
                    warnings.append(f"{current_path} contains redacted sensitive content.")
                else:
                    failures.append(f"{current_path} exposes sensitive content.")
            _scan_sensitive_content(item, current_path, warnings, failures)
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_sensitive_content(item, f"{field_path}[{index}]", warnings, failures)
        return

    if not isinstance(value, str):
        return

    lowered = value.lower()
    if "/home/" in value:
        failures.append(f"{field_path} contains an absolute local path.")
    if "potcar" in lowered and not (field_path.endswith(".name") or field_path.endswith(".path")):
        failures.append(f"{field_path} references POTCAR content.")
    if any(part in lowered for part in SENSITIVE_KEY_PARTS):
        if _is_redacted(value):
            warnings.append(f"{field_path} contains redacted sensitive text.")
        elif field_path.endswith("field") or field_path.endswith("message") or field_path.endswith("type"):
            warnings.append(f"{field_path} mentions sensitive text in a descriptive field.")
        else:
            warnings.append(f"{field_path} contains sensitive keyword text.")


def _derive_source_artifact_ids(
    explicit_source_artifact_ids: list[str] | None,
    final_handoff: dict[str, Any] | None,
    artifacts: list[dict[str, Any]],
    core_artifacts: list[dict[str, Any]],
) -> list[str]:
    if explicit_source_artifact_ids:
        return _dedupe(list(explicit_source_artifact_ids))
    candidate_ids = []
    if isinstance(final_handoff, dict):
        candidate_ids.extend(final_handoff.get("source_artifact_ids", []))
    for artifact in core_artifacts:
        candidate_ids.extend(artifact.get("lineage", {}).get("parent_artifacts", []))
    writing_artifact_ids = {
        artifact.get("artifact_id")
        for artifact in artifacts
        if artifact.get("stage") == "writing"
    }
    return _dedupe([artifact_id for artifact_id in candidate_ids if artifact_id and artifact_id not in writing_artifact_ids])


def _check_required_writing_outputs(
    project_root: Path,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_files = []
    missing_artifacts = []
    for name, relative_path in REQUIRED_WRITING_OUTPUTS.items():
        if not (project_root / relative_path).is_file():
            missing_files.append(name)
        if _latest_artifact(artifacts, name=name, stage="writing") is None:
            missing_artifacts.append(name)
    if missing_files or missing_artifacts:
        return {
            "status": "fail",
            "message": "Required writing deliverables are missing.",
            "details": {
                "missing_files": missing_files,
                "missing_artifacts": missing_artifacts,
            },
        }
    return {
        "status": "pass",
        "message": "All required writing deliverables are present and registered.",
        "details": {"outputs": list(REQUIRED_WRITING_OUTPUTS.keys())},
    }


def _check_artifact_traceability(
    artifacts: list[dict[str, Any]],
    final_handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    tracked_names = [
        *REQUIRED_WRITING_OUTPUTS.keys(),
        "reproducibility_manifest.json",
    ]
    missing_artifacts = []
    missing_lineage = []
    traceable = []
    source_artifact_ids = final_handoff.get("source_artifact_ids", []) if isinstance(final_handoff, dict) else []
    for name in tracked_names:
        artifact = _latest_artifact(artifacts, name=name, stage="writing")
        if artifact is None:
            missing_artifacts.append(name)
            continue
        parent_artifacts = artifact.get("lineage", {}).get("parent_artifacts", [])
        if parent_artifacts or source_artifact_ids:
            traceable.append(name)
        else:
            missing_lineage.append(name)
    if missing_artifacts or missing_lineage:
        return {
            "status": "fail",
            "message": "Traceability is incomplete for final delivery artifacts.",
            "details": {
                "missing_artifacts": missing_artifacts,
                "missing_lineage": missing_lineage,
                "traceable": traceable,
            },
        }
    return {
        "status": "pass",
        "message": "Final delivery artifacts have traceable lineage.",
        "details": {"traceable": traceable},
    }


def _check_compute_truth(
    reproducibility_manifest: dict[str, Any] | None,
    final_handoff: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    required_keys = ["dry_run", "real_submit", "approval_required_for_real_submit"]
    manifest_truth = reproducibility_manifest.get("execution_truth", {}) if isinstance(reproducibility_manifest, dict) else {}
    handoff_truth = final_handoff.get("compute_truth", {}) if isinstance(final_handoff, dict) else {}
    manifest_complete = all(key in manifest_truth for key in required_keys)
    handoff_complete = all(key in handoff_truth for key in required_keys)
    mismatched_keys = []
    if manifest_complete and handoff_complete:
        for key in required_keys:
            if bool(manifest_truth.get(key)) != bool(handoff_truth.get(key)):
                mismatched_keys.append(key)
    if mismatched_keys:
        return {
            "status": "fail",
            "message": "Compute truth declarations disagree across final delivery reports.",
            "details": {"mismatched_keys": mismatched_keys},
        }, {}
    selected_truth = handoff_truth if handoff_complete else manifest_truth if manifest_complete else {}
    if not selected_truth:
        return {
            "status": "fail",
            "message": "Compute truth is not declared in final handoff or reproducibility manifest.",
            "details": {},
        }, {}
    details = {key: bool(selected_truth.get(key)) for key in required_keys}
    return {
        "status": "pass",
        "message": "Compute truth is declared for final delivery.",
        "details": details,
    }, selected_truth


def _check_real_submit_approval(selected_truth: dict[str, Any]) -> dict[str, Any]:
    if not selected_truth:
        return {
            "status": "fail",
            "message": "Cannot validate real submit approval without compute truth.",
            "details": {},
        }
    real_submit = bool(selected_truth.get("real_submit", False))
    approval_required = bool(
        selected_truth.get(
            "approval_required_for_real_submit",
            selected_truth.get("approval_required", True),
        )
    )
    gate_status = selected_truth.get("approval_gate_status") or selected_truth.get("gate_status")
    if not real_submit:
        return {
            "status": "pass",
            "message": "No real submit was declared.",
            "details": {
                "real_submit": real_submit,
                "approval_required_for_real_submit": approval_required,
            },
        }
    if not approval_required:
        return {
            "status": "fail",
            "message": "Real submit was declared without an approval requirement.",
            "details": {
                "real_submit": real_submit,
                "approval_required_for_real_submit": approval_required,
            },
        }
    if gate_status is None:
        return {
            "status": "fail",
            "message": "Real submit was declared without a recorded approval gate outcome.",
            "details": {
                "real_submit": real_submit,
                "approval_required_for_real_submit": approval_required,
            },
        }
    if str(gate_status).lower() not in APPROVED_GATE_STATUSES:
        return {
            "status": "fail",
            "message": "Real submit was declared but the approval gate did not pass.",
            "details": {
                "real_submit": real_submit,
                "approval_required_for_real_submit": approval_required,
                "approval_gate_status": gate_status,
            },
        }
    return {
        "status": "pass",
        "message": "Real submit declaration includes an approved gate outcome.",
        "details": {
            "real_submit": real_submit,
            "approval_required_for_real_submit": approval_required,
            "approval_gate_status": gate_status,
        },
    }


def _check_sensitive_content(
    reproducibility_manifest: dict[str, Any] | None,
    final_handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    failures: list[str] = []
    _scan_sensitive_content(reproducibility_manifest or {}, "reproducibility_manifest", warnings, failures)
    _scan_sensitive_content(final_handoff or {}, "final_handoff", warnings, failures)
    status = "fail" if failures else "warning" if warnings else "pass"
    if status == "pass":
        message = "No sensitive paths or secret-like content were detected in final delivery reports."
    elif status == "warning":
        message = "Sensitive-looking content appears only in redacted or descriptive form."
    else:
        message = "Sensitive path or secret leakage was detected in final delivery reports."
    return {
        "status": status,
        "message": message,
        "details": {
            "warnings": _dedupe(warnings),
            "failures": _dedupe(failures),
        },
    }


def _check_checkpoint_summary(
    checkpoints: list[dict[str, Any]],
    reproducibility_manifest: dict[str, Any] | None,
    final_handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    checkpoint_summary = reproducibility_manifest.get("checkpoint_summary", {}) if isinstance(reproducibility_manifest, dict) else {}
    latest_checkpoint = final_handoff.get("latest_checkpoint") if isinstance(final_handoff, dict) else None
    if checkpoint_summary and (checkpoint_summary.get("latest") or latest_checkpoint):
        return {
            "status": "pass",
            "message": "Checkpoint summary is present in final delivery reports.",
            "details": {
                "count": checkpoint_summary.get("count"),
                "latest_checkpoint": (checkpoint_summary.get("latest") or latest_checkpoint),
            },
        }
    if checkpoints:
        return {
            "status": "warning",
            "message": "Checkpoint records exist but final delivery summary is incomplete.",
            "details": {"checkpoint_count": len(checkpoints)},
        }
    return {
        "status": "warning",
        "message": "No checkpoint summary is available for final delivery.",
        "details": {},
    }


def build_final_delivery_report(
    base_dir: str = ".",
    project_root: Optional[str] = None,
    source_artifact_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    workflow = read_state(project_root=str(root), state_file="workflow.json")
    if not workflow:
        raise FileNotFoundError("No workflow state found")
    checkpoints_state = read_state(project_root=str(root), state_file="checkpoints.json")
    artifacts_state = read_state(project_root=str(root), state_file="artifacts.json")
    checkpoints = checkpoints_state if isinstance(checkpoints_state, list) else []
    artifacts = artifacts_state if isinstance(artifacts_state, list) else []
    reproducibility_manifest = _load_json(_report_path(root, REPRODUCIBILITY_MANIFEST_FILE))
    final_handoff = _load_json(_report_path(root, FINAL_HANDOFF_FILE))
    core_artifacts = [
        artifact
        for artifact in (
            *(_latest_artifact(artifacts, name=name, stage="writing") for name in REQUIRED_WRITING_OUTPUTS),
            _latest_artifact(artifacts, name="reproducibility_manifest.json", stage="writing"),
        )
        if artifact is not None
    ]
    report = create_verification_report(
        "writing",
        workflow.get("workflow_id", "unknown"),
        base_dir=str(root),
        source_artifact_ids=_derive_source_artifact_ids(source_artifact_ids, final_handoff, artifacts, core_artifacts),
    )
    add_check(report, "artifact_traceability", **_check_artifact_traceability(artifacts, final_handoff))
    add_check(report, "required_writing_outputs", **_check_required_writing_outputs(root, artifacts))
    add_check(
        report,
        "reproducibility_manifest_present",
        status="pass" if reproducibility_manifest else "fail",
        message="Reproducibility manifest is present." if reproducibility_manifest else "Reproducibility manifest is missing.",
        details={"path": REPRODUCIBILITY_MANIFEST_FILE},
    )
    add_check(
        report,
        "final_handoff_present",
        status="pass" if final_handoff else "fail",
        message="Final handoff JSON is present." if final_handoff else "Final handoff JSON is missing.",
        details={"path": FINAL_HANDOFF_FILE},
    )
    compute_truth_check, selected_truth = _check_compute_truth(reproducibility_manifest, final_handoff)
    add_check(report, "compute_truth_declared", **compute_truth_check)
    add_check(report, "no_real_submit_without_approval", **_check_real_submit_approval(selected_truth))
    add_check(report, "no_sensitive_paths", **_check_sensitive_content(reproducibility_manifest, final_handoff))
    add_check(report, "checkpoint_summary_present", **_check_checkpoint_summary(checkpoints, reproducibility_manifest, final_handoff))
    return _complete_report(report)
