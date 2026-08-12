"""Evidence-boundary classification for literature helper results."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


METADATA_STATES = {"discovered", "cross_checked", "conflicted"}
FULL_TEXT_STATES = {"unavailable", "available", "inspected"}
CLAIM_STATES = {"unverified", "partially_verified", "verified"}


def initial_evidence_state(
    *,
    observation_count: int = 0,
    conflicts: list[dict[str, Any]] | None = None,
    full_text_available: bool = False,
) -> dict[str, Any]:
    """Create an evidence state without inferring reading or claim verification."""
    conflict_items = list(conflicts or [])
    metadata = "conflicted" if conflict_items else "cross_checked" if observation_count >= 2 else "discovered"
    return {
        "metadata": metadata,
        "full_text": "available" if full_text_available else "unavailable",
        "claims": "unverified",
        "inspection_locators": [],
        "claim_verifications": [],
    }


def mark_full_text_available(state: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    """Mark a legal or user-provided full-text candidate as available."""
    result = _state(state)
    if not candidate.get("path") and not candidate.get("url"):
        raise ValueError("Full-text availability requires a path or URL")
    if candidate.get("access_basis") not in {
        "user_provided",
        "open_access",
        "institutional_entitlement",
        "publisher_api",
    }:
        raise ValueError("Unsupported or undeclared full-text access basis")
    if result["full_text"] == "unavailable":
        result["full_text"] = "available"
    return result


def mark_full_text_inspected(
    state: dict[str, Any] | None,
    *,
    locators: list[str],
) -> dict[str, Any]:
    """Record actual inspected sections/pages; file availability alone is insufficient."""
    result = _state(state)
    cleaned = [str(item).strip() for item in locators if str(item).strip()]
    if result["full_text"] == "unavailable":
        raise ValueError("Full text must be available before it can be inspected")
    if not cleaned:
        raise ValueError("Full-text inspection requires explicit page or section locators")
    result["full_text"] = "inspected"
    result["inspection_locators"] = sorted(set(result["inspection_locators"] + cleaned))
    return result


def mark_claim_verified(
    state: dict[str, Any] | None,
    *,
    claim: str,
    locators: list[str],
    verdict: str = "verified",
) -> dict[str, Any]:
    """Record one claim check without promoting unrelated claims."""
    result = _state(state)
    claim_text = str(claim).strip()
    cleaned = [str(item).strip() for item in locators if str(item).strip()]
    if result["full_text"] != "inspected":
        raise ValueError("Claim verification requires inspected full text")
    if not claim_text or not cleaned:
        raise ValueError("Claim verification requires a claim and source locators")
    if verdict not in {"verified", "partially_verified", "contradicted"}:
        raise ValueError(f"Unsupported claim-verification verdict: {verdict}")
    result["claim_verifications"].append(
        {"claim": claim_text, "locators": cleaned, "verdict": verdict}
    )
    verdicts = {item["verdict"] for item in result["claim_verifications"]}
    result["claims"] = "verified" if verdicts == {"verified"} else "partially_verified"
    return result


def display_evidence_level(state: dict[str, Any] | None) -> str:
    """Return the highest honest user-facing evidence boundary."""
    result = _state(state)
    if result["claims"] == "verified":
        return "claim_verified"
    if result["full_text"] == "inspected":
        return "full_text_inspected"
    if result["full_text"] == "available":
        return "full_text_available"
    return "metadata_only"


def _state(state: dict[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(state or initial_evidence_state())
    if result.get("metadata") not in METADATA_STATES:
        raise ValueError("Invalid metadata evidence state")
    if result.get("full_text") not in FULL_TEXT_STATES:
        raise ValueError("Invalid full-text evidence state")
    if result.get("claims") not in CLAIM_STATES:
        raise ValueError("Invalid claim evidence state")
    result.setdefault("inspection_locators", [])
    result.setdefault("claim_verifications", [])
    return result


__all__ = [
    "display_evidence_level",
    "initial_evidence_state",
    "mark_claim_verified",
    "mark_full_text_available",
    "mark_full_text_inspected",
]
