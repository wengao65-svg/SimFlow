"""Verification report data structures and execution framework."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


VERIFICATION_FILE = ".simflow/state/verification.json"


def create_verification_report(
    stage: str,
    workflow_id: str,
    base_dir: str = ".",
) -> dict:
    """Create a new verification report for a stage."""
    report = {
        "stage": stage,
        "workflow_id": workflow_id,
        "status": "pending",
        "checks": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    return report


def add_check(
    report: dict,
    name: str,
    status: str,
    message: str = "",
    details: Optional[dict] = None,
) -> dict:
    """Add a verification check result to a report."""
    check = {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    report["checks"].append(check)
    return report


def finalize_report(report: dict, base_dir: str = ".") -> dict:
    """Finalize a verification report and persist it."""
    overall = "pass"
    for c in report["checks"]:
        if c["status"] == "fail":
            overall = "fail"
            break
        elif c["status"] == "warning":
            overall = "warning"
    report["status"] = overall
    report["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Persist
    path = Path(base_dir) / VERIFICATION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.append(report)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return report


def get_verifications(stage: Optional[str] = None, base_dir: str = ".") -> list:
    """Get verification reports, optionally filtered by stage."""
    path = Path(base_dir) / VERIFICATION_FILE
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        reports = json.load(f)
    if stage:
        return [r for r in reports if r.get("stage") == stage]
    return reports


def run_checks(
    stage: str,
    workflow_id: str,
    checks: list,
    base_dir: str = ".",
) -> dict:
    """Run a list of verification checks and produce a report.

    Args:
        checks: list of (name, check_fn) tuples where check_fn returns
                {"status": str, "message": str, "details": dict}
    """
    report = create_verification_report(stage, workflow_id, base_dir)
    for name, check_fn in checks:
        try:
            result = check_fn()
            add_check(report, name, **result)
        except Exception as e:
            add_check(report, name, status="fail", message=str(e))
    return finalize_report(report, base_dir)
