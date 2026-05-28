"""Read-only stage readiness diagnostics for SimFlow projects."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .state import resolve_project_root
from .status import _artifact_path_status, _lineage_links, _read_project_state, _stage_sequence


ROOT = Path(__file__).resolve().parents[2]
STAGES_DIR = ROOT / "workflow" / "stages"
APPROVED_DECISIONS = {"approve", "approved", "allow", "allowed", "pass", "passed"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_key(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _evidence_key(entry: Any) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        for key in ("id", "key", "type", "name"):
            if entry.get(key):
                return str(entry[key])
    return str(entry)


def _load_stage_contract(stage: str) -> dict[str, Any] | None:
    path = STAGES_DIR / f"{stage}.json"
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else None


def _choose_stage(state: dict[str, Any], requested_stage: str | None) -> str | None:
    if requested_stage:
        return requested_stage
    workflow = state["workflow"]
    current_stage = workflow.get("current_stage") or state["metadata"].get("current_stage")
    if current_stage:
        return str(current_stage)

    stages = _stage_sequence(workflow, state["metadata"])
    registry = state["stages"]
    for stage in stages:
        if _as_dict(registry.get(stage)).get("status") == "in_progress":
            return stage
    return stages[0] if stages else None


def _artifact_evidence_keys(artifact: dict[str, Any]) -> set[str]:
    metadata = _as_dict(artifact.get("metadata"))
    keys = {
        _normalize_key(artifact.get("type")),
        _normalize_key(Path(str(artifact.get("name") or "")).stem),
    }
    if artifact.get("path"):
        keys.add(_normalize_key(Path(str(artifact["path"])).stem))
    if metadata.get("evidence_key"):
        keys.add(_normalize_key(metadata["evidence_key"]))
    for key in _as_list(metadata.get("evidence_keys")):
        keys.add(_normalize_key(key))
    return {key for key in keys if key}


def _match_evidence(contract: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for entry in _as_list(contract.get("evidence_outputs")):
        key = _evidence_key(entry)
        normalized = _normalize_key(key)
        matches = [
            artifact
            for artifact in artifacts
            if normalized and normalized in _artifact_evidence_keys(artifact)
        ]
        checks.append({
            "evidence_key": key,
            "present": bool(matches),
            "matching_artifact_ids": [artifact.get("artifact_id") for artifact in matches],
            "matching_artifact_names": [artifact.get("name") for artifact in matches],
        })
    return checks


def _stage_checkpoint_present(stage: str, stage_state: dict[str, Any], checkpoints: list[Any]) -> bool:
    checkpoint_id = stage_state.get("checkpoint_id")
    if checkpoint_id:
        return True
    return any(
        isinstance(checkpoint, dict) and checkpoint.get("stage_id") == stage
        for checkpoint in checkpoints
    )


def _stage_missing_paths(root: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = []
    for artifact in artifacts:
        status = _artifact_path_status(root, artifact)
        if status and not status["exists"]:
            missing.append(status)
    return missing


def _stage_missing_lineage_parents(
    stage: str,
    artifacts: list[dict[str, Any]],
    lineage_state: dict[str, Any],
) -> list[dict[str, Any]]:
    _, missing = _lineage_links(artifacts, lineage_state)
    stage_artifact_ids = {
        artifact.get("artifact_id")
        for artifact in artifacts
        if artifact.get("stage") == stage
    }
    return [
        item for item in missing
        if item.get("child_artifact_id") in stage_artifact_ids
    ]


def _has_real_submit_evidence(stage_artifacts: list[dict[str, Any]]) -> bool:
    for artifact in stage_artifacts:
        metadata = _as_dict(artifact.get("metadata"))
        lineage_parameters = _as_dict(_as_dict(artifact.get("lineage")).get("parameters"))
        keys = _artifact_evidence_keys(artifact)
        if "job_record_if_submitted" in keys or "job_record" in keys:
            return True
        for payload in (metadata, lineage_parameters):
            execution_truth = _as_dict(payload.get("execution_truth"))
            if payload.get("real_submit") is True or execution_truth.get("real_submit") is True:
                return True
    return False


def _approved_hpc_decision(gates: dict[str, Any]) -> dict[str, Any] | None:
    latest = _as_dict(gates.get("hpc_submit"))
    latest_decision = str(latest.get("latest_decision") or "").lower()
    if latest_decision in APPROVED_DECISIONS:
        return {
            "decision_id": latest.get("latest_decision_id"),
            "decision": latest.get("latest_decision"),
            "decided_at": latest.get("latest_decision_at"),
        }
    for decision in reversed(_as_list(gates.get("decisions"))):
        if not isinstance(decision, dict):
            continue
        if decision.get("gate") != "hpc_submit":
            continue
        if str(decision.get("decision") or "").lower() in APPROVED_DECISIONS:
            return {
                "decision_id": decision.get("decision_id"),
                "decision": decision.get("decision"),
                "decided_at": decision.get("timestamp"),
            }
    return None


def _build_actions(
    stage: str,
    missing_evidence: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    stage_status: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in missing_evidence:
        actions.append({
            "action": "record_evidence_artifact",
            "stage": stage,
            "evidence_key": item["evidence_key"],
            "reason": "required_stage_evidence_missing",
        })
    for blocker in blockers:
        if blocker["code"] == "missing_workflow_state":
            actions.append({"action": "initialize_workflow", "stage": stage, "reason": blocker["code"]})
        elif blocker["code"] == "missing_stage_contract":
            actions.append({"action": "define_or_select_canonical_stage", "stage": stage, "reason": blocker["code"]})
        elif blocker["code"] == "missing_checkpoint":
            actions.append({"action": "create_checkpoint", "stage": stage, "reason": blocker["code"]})
        elif blocker["code"] == "missing_artifact_paths":
            actions.append({"action": "restore_or_reregister_artifact_paths", "stage": stage, "reason": blocker["code"]})
        elif blocker["code"] == "missing_lineage_parents":
            actions.append({"action": "repair_artifact_lineage", "stage": stage, "reason": blocker["code"]})
        elif blocker["code"] == "missing_hpc_submit_approval":
            actions.append({"action": "record_hpc_submit_approval", "stage": stage, "reason": blocker["code"]})
    if not actions and stage_status == "pending":
        actions.append({"action": "start_stage", "stage": stage, "reason": "stage_pending"})
    if not actions and stage_status == "in_progress":
        actions.append({"action": "complete_or_checkpoint_stage", "stage": stage, "reason": "stage_in_progress"})
    return actions


def build_stage_readiness(project_root: str, stage: str | None = None) -> dict[str, Any]:
    """Build a read-only readiness diagnostic for one stage."""
    root = resolve_project_root(project_root=project_root)
    state = _read_project_state(root)
    selected_stage = _choose_stage(state, stage)
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not state["workflow"]:
        selected_stage = selected_stage or stage or "literature_review"
        blockers.append({
            "code": "missing_workflow_state",
            "severity": "high",
            "message": "No workflow state is recorded.",
        })

    if selected_stage is None:
        selected_stage = "unknown"
        blockers.append({
            "code": "missing_stage_selection",
            "severity": "high",
            "message": "No stage could be selected from workflow state.",
        })

    contract = _load_stage_contract(selected_stage)
    if contract is None:
        blockers.append({
            "code": "missing_stage_contract",
            "severity": "high",
            "message": f"No stage contract exists for {selected_stage}.",
        })
        contract = {"name": selected_stage, "evidence_outputs": []}

    artifacts = [
        artifact for artifact in state["artifacts"]
        if isinstance(artifact, dict) and artifact.get("stage") == selected_stage
    ]
    stage_state = _as_dict(state["stages"].get(selected_stage))
    stage_status = stage_state.get("status", "pending")
    evidence_checks = _match_evidence(contract, artifacts)
    missing_evidence = [item for item in evidence_checks if not item["present"]]
    missing_paths = _stage_missing_paths(root, artifacts)
    missing_parents = _stage_missing_lineage_parents(selected_stage, state["artifacts"], state["lineage"])

    if missing_paths:
        blockers.append({
            "code": "missing_artifact_paths",
            "severity": "medium",
            "message": f"{len(missing_paths)} artifact path(s) are missing for {selected_stage}.",
            "artifacts": missing_paths,
        })
    if missing_parents:
        blockers.append({
            "code": "missing_lineage_parents",
            "severity": "medium",
            "message": f"{len(missing_parents)} lineage parent reference(s) are missing for {selected_stage}.",
            "lineage": missing_parents,
        })
    if stage_status == "completed" and not _stage_checkpoint_present(selected_stage, stage_state, state["checkpoints"]):
        blockers.append({
            "code": "missing_checkpoint",
            "severity": "medium",
            "message": f"Completed stage {selected_stage} does not have a checkpoint.",
        })

    approval_triggers = _as_list(contract.get("approval_triggers"))
    approval_state = {"triggers": approval_triggers, "hpc_submit_decision": _approved_hpc_decision(state["gates"])}
    if selected_stage == "computation" and _has_real_submit_evidence(artifacts) and approval_state["hpc_submit_decision"] is None:
        blockers.append({
            "code": "missing_hpc_submit_approval",
            "severity": "high",
            "message": "Computation records real submit evidence but no approved hpc_submit gate decision.",
        })
    elif approval_triggers:
        warnings.append({
            "code": "approval_triggers_present",
            "severity": "info",
            "message": f"Stage {selected_stage} has approval triggers to review before risky actions.",
            "triggers": approval_triggers,
        })

    readiness_status = "blocked" if blockers else "incomplete" if missing_evidence else "ready"
    return {
        "status": "success",
        "project_root": str(root),
        "stage": selected_stage,
        "readiness_status": readiness_status,
        "stage_status": stage_status,
        "contract": {
            "intent": contract.get("intent"),
            "evidence_outputs": [_evidence_key(entry) for entry in _as_list(contract.get("evidence_outputs"))],
            "suggested_checks": _as_list(contract.get("suggested_checks")),
            "approval_triggers": approval_triggers,
            "handoff_notes": _as_list(contract.get("handoff_notes")),
        },
        "evidence": {
            "required_count": len(evidence_checks),
            "present_count": len([item for item in evidence_checks if item["present"]]),
            "missing_count": len(missing_evidence),
            "items": evidence_checks,
        },
        "artifacts": {
            "count": len(artifacts),
            "artifact_ids": [artifact.get("artifact_id") for artifact in artifacts],
            "missing_paths": missing_paths,
        },
        "lineage": {
            "missing_parents": missing_parents,
        },
        "checkpoint": {
            "required": stage_status == "completed",
            "present": _stage_checkpoint_present(selected_stage, stage_state, state["checkpoints"]),
            "checkpoint_id": stage_state.get("checkpoint_id"),
        },
        "approval": approval_state,
        "warnings": warnings,
        "blockers": blockers,
        "actions": _build_actions(selected_stage, missing_evidence, blockers, stage_status),
    }


def build_project_readiness(project_root: str) -> dict[str, Any]:
    """Build read-only readiness diagnostics for all stages in a project."""
    root = resolve_project_root(project_root=project_root)
    state = _read_project_state(root)
    stages = _stage_sequence(state["workflow"], state["metadata"])
    if not stages:
        stages = ["literature_review"]
    stage_results = [build_stage_readiness(str(root), stage=stage) for stage in stages]
    if any(item["readiness_status"] == "blocked" for item in stage_results):
        readiness_status = "blocked"
    elif any(item["readiness_status"] == "incomplete" for item in stage_results):
        readiness_status = "incomplete"
    else:
        readiness_status = "ready"
    return {
        "status": "success",
        "project_root": str(root),
        "readiness_status": readiness_status,
        "stages": stage_results,
        "actions": [
            action
            for stage_result in stage_results
            for action in stage_result.get("actions", [])
        ],
    }
