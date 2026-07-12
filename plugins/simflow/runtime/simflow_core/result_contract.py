"""Canonical result contract helpers for SimFlow runtime records."""

from __future__ import annotations

from typing import Any

from .helper_evidence import SCHEMA_VERSION as HELPER_EVIDENCE_SCHEMA_VERSION


SCHEMA_VERSION = "simflow.result.v1"
ROLES = ("helper", "stage_runner", "state_admin")
OUTCOMES = ("success", "warning", "waiting", "blocked", "error", "skipped")
STATE_EFFECTS = ("none", "record_only", "stage_transition", "checkpoint_admin")

_SUCCESS_STATUSES = {
    "success",
    "completed",
    "classified",
    "ready",
    "pass",
    "parsed",
    "executed",
    "supported",
}
_WARNING_STATUSES = {
    "warning",
    "partial",
    "unavailable",
}
_WAITING_STATUSES = {
    "waiting",
    "waiting_for_outputs",
    "needs_inputs",
    "needs_clarification",
    "approval_required",
    "required_for_real_submit",
    "not_evaluated",
    "planned",
    "dry_run",
    "dry_run_complete",
    "would_execute",
    "in_progress",
    "missing",
    "capability_warning",
}
_BLOCKED_STATUSES = {
    "blocked",
    "block",
    "failed",
    "fail",
    "missing_outputs",
    "unsupported",
}
_ERROR_STATUSES = {
    "error",
    "failure",
    "corrupted",
    "malformed",
}
_SKIPPED_STATUSES = {
    "skip",
    "skipped",
    "skipped_optional_dependency",
    "not_applicable",
}


def _normalize_enum(value: str, *, allowed: tuple[str, ...], field: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return normalized


def normalize_result_outcome(status: Any) -> str:
    """Map legacy status strings to the conservative canonical outcome enum."""
    normalized = str(status or "warning").strip().lower()
    if normalized in _SUCCESS_STATUSES:
        return "success"
    if normalized in _WARNING_STATUSES:
        return "warning"
    if normalized in _WAITING_STATUSES:
        return "waiting"
    if normalized in _BLOCKED_STATUSES:
        return "blocked"
    if normalized in _ERROR_STATUSES:
        return "error"
    if normalized in _SKIPPED_STATUSES:
        return "skipped"
    return "warning"


def build_simflow_result(
    *,
    role: str,
    activity: str,
    legacy_status: Any,
    stage: str | None = None,
    outcome: str | None = None,
    reason_code: str | None = None,
    state_effect: str = "none",
    **extra: Any,
) -> dict[str, Any]:
    """Build a canonical nested result record."""
    record = {
        "schema_version": SCHEMA_VERSION,
        "role": _normalize_enum(role, allowed=ROLES, field="role"),
        "activity": activity,
        "legacy_status": legacy_status,
        "outcome": normalize_result_outcome(legacy_status)
        if outcome is None
        else _normalize_enum(outcome, allowed=OUTCOMES, field="outcome"),
        "state_effect": _normalize_enum(state_effect, allowed=STATE_EFFECTS, field="state_effect"),
    }
    if stage is not None:
        record["stage"] = stage
    if reason_code is not None:
        record["reason_code"] = reason_code
    record.update(extra)
    return record


def attach_simflow_result(
    result: dict[str, Any],
    *,
    role: str,
    activity: str,
    legacy_status: Any,
    stage: str | None = None,
    outcome: str | None = None,
    reason_code: str | None = None,
    state_effect: str = "none",
    **extra: Any,
) -> dict[str, Any]:
    """Attach a canonical nested result while preserving top-level fields."""
    result["simflow_result"] = build_simflow_result(
        role=role,
        activity=activity,
        legacy_status=legacy_status,
        stage=stage,
        outcome=outcome,
        reason_code=reason_code,
        state_effect=state_effect,
        **extra,
    )
    return result


def extract_helper_evidence_payload(result: Any) -> dict[str, Any] | None:
    """Return helper evidence from nested payloads or top-level records."""
    if not isinstance(result, dict):
        return None
    nested = result.get("helper_evidence")
    if isinstance(nested, dict):
        return nested
    version_key = result.get(HELPER_EVIDENCE_SCHEMA_VERSION)
    if isinstance(version_key, dict):
        return version_key
    if result.get("schema_version") == HELPER_EVIDENCE_SCHEMA_VERSION:
        return result
    return None
