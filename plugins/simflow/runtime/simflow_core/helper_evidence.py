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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", False):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


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


def extract_helper_evidence_metadata(artifact: dict[str, Any]) -> dict[str, Any]:
    """Extract common helper-evidence metadata from a registered artifact."""
    metadata = _as_dict(artifact.get("metadata"))
    helper_evidence = _as_dict(metadata.get("helper_evidence"))
    source = helper_evidence or metadata
    actual_tool_used = _as_dict(source.get("actual_tool_used") or metadata.get("actual_tool_used"))
    lineage = _as_dict(artifact.get("lineage"))
    parameters = _as_dict(lineage.get("parameters"))
    tool = (
        actual_tool_used.get("name")
        or actual_tool_used.get("software")
        or metadata.get("software")
        or parameters.get("software")
        or parameters.get("tool")
        or lineage.get("software")
    )
    claim_ids: list[str] = []
    for value in (
        source.get("claim_id"),
        metadata.get("claim_id"),
        parameters.get("claim_id"),
    ):
        claim_ids.extend(str(item) for item in _as_list(value) if item)
    for key in ("claim_ids", "claims"):
        for value in _as_list(source.get(key)) + _as_list(metadata.get(key)) + _as_list(parameters.get(key)):
            if isinstance(value, dict):
                claim_id = value.get("claim_id") or value.get("id")
                if claim_id:
                    claim_ids.append(str(claim_id))
            elif value:
                claim_ids.append(str(value))
    return {
        "schema_version": source.get("schema_version"),
        "helper": source.get("helper") or metadata.get("helper_name"),
        "capability": source.get("capability"),
        "activity": source.get("activity"),
        "stage": source.get("stage") or artifact.get("stage"),
        "evidence_role": source.get("evidence_role") or metadata.get("evidence_role") or metadata.get("role"),
        "helper_status": source.get("status") or metadata.get("helper_result_status"),
        "parser_status": source.get("parser_status"),
        "actual_tool_used": actual_tool_used,
        "tool": tool,
        "recipe": source.get("recipe") or metadata.get("recipe") or parameters.get("recipe"),
        "claim_limits": source.get("claim_limits") or metadata.get("claim_limits") or [],
        "warnings": source.get("warnings") or metadata.get("warnings") or [],
        "limitations": source.get("limitations") or metadata.get("limitations") or [],
        "claim_ids": list(dict.fromkeys(claim_ids)),
    }


def helper_evidence_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    """Return a compact helper-evidence summary suitable for graph nodes."""
    evidence = extract_helper_evidence_metadata(artifact)
    return {
        "schema_version": evidence.get("schema_version"),
        "helper": evidence.get("helper"),
        "evidence_role": evidence.get("evidence_role"),
        "actual_tool_used": evidence.get("actual_tool_used"),
        "helper_status": evidence.get("helper_status"),
        "parser_status": evidence.get("parser_status"),
        "recipe": evidence.get("recipe"),
        "claim_ids": evidence.get("claim_ids", []),
    }
