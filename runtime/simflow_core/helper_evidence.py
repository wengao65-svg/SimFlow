"""Lightweight helper-produced evidence contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "simflow.helper_evidence.v1"
VALID_STATUSES = {
    "success",
    "warning",
    "blocked",
    "incomplete",
    "skipped_optional_dependency",
    "capability_warning",
}
VALID_PARSER_STATUSES = {
    "parsed",
    "partial",
    "unrecognized",
    "missing",
    "malformed",
    "not_applicable",
}

_STATUS_ALIASES = {
    "pass": "success",
    "passed": "success",
    "ready": "success",
    "error": "blocked",
    "failed": "blocked",
    "fail": "blocked",
    "block": "blocked",
}

_PARSER_STATUS_ALIASES = {
    "unparsed": "unrecognized",
    "unknown": "unrecognized",
    "skipped": "not_applicable",
}


def normalize_helper_status(status: Any) -> str:
    """Normalize helper status strings into the common evidence vocabulary."""
    normalized = str(status or "incomplete").strip().lower()
    normalized = _STATUS_ALIASES.get(normalized, normalized)
    return normalized if normalized in VALID_STATUSES else "incomplete"


def normalize_parser_status(status: Any) -> str:
    """Normalize parser status strings into the common evidence vocabulary."""
    normalized = str(status or "not_applicable").strip().lower()
    normalized = _PARSER_STATUS_ALIASES.get(normalized, normalized)
    return normalized if normalized in VALID_PARSER_STATUSES else "unrecognized"


def sha256_file(path: str | Path) -> str | None:
    """Return sha256 for a regular file, or None when absent."""
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        return None
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_file_record(path: str | Path, *, role: str | None = None) -> dict[str, Any]:
    """Build a non-invasive source file metadata record."""
    candidate = Path(path).expanduser()
    record = {
        "path": str(candidate),
        "present": candidate.exists(),
        "is_file": candidate.is_file(),
        "bytes": candidate.stat().st_size if candidate.is_file() else None,
        "sha256": sha256_file(candidate),
    }
    if role:
        record["role"] = role
    return record


def build_helper_evidence(
    *,
    helper: str,
    capability: str,
    status: str,
    stage: str,
    activity: str,
    evidence_role: str,
    source_files: list[Any] | None = None,
    actual_tool_used: dict[str, Any] | None = None,
    parser_status: str = "not_applicable",
    claim_limits: list[str] | None = None,
    warnings: list[Any] | None = None,
    limitations: list[str] | None = None,
    parent_artifacts: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Create a helper evidence envelope without enforcing a global schema gate."""
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "helper": helper,
        "capability": capability,
        "status": normalize_helper_status(status),
        "stage": stage,
        "activity": activity,
        "evidence_role": evidence_role,
        "source_files": source_files or [],
        "actual_tool_used": actual_tool_used or {},
        "parser_status": normalize_parser_status(parser_status),
        "claim_limits": claim_limits or [],
        "warnings": warnings or [],
        "limitations": limitations or [],
        "parent_artifacts": parent_artifacts or [],
    }
    evidence.update(extra)
    return evidence
