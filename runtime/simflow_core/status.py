"""Read-only project status, evidence graph, and handoff summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .state import read_state, resolve_project_root
from .workflow import CANONICAL_STAGES, load_recipe


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_project_state(root: Path) -> dict[str, Any]:
    return {
        "workflow": _as_dict(read_state(project_root=str(root), state_file="workflow.json")),
        "metadata": _as_dict(read_state(project_root=str(root), state_file="metadata.json")),
        "stages": _as_dict(read_state(project_root=str(root), state_file="stages.json")),
        "artifacts": _as_list(read_state(project_root=str(root), state_file="artifacts.json")),
        "checkpoints": _as_list(read_state(project_root=str(root), state_file="checkpoints.json")),
        "lineage": _as_dict(read_state(project_root=str(root), state_file="lineage.json")),
        "gates": _as_dict(read_state(project_root=str(root), state_file="gates.json")),
        "verification": _as_dict(read_state(project_root=str(root), state_file="verification.json")),
    }


def _stage_sequence(workflow: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    candidates = metadata.get("canonical_stages") or metadata.get("stages") or []
    if isinstance(candidates, list) and candidates:
        return [stage for stage in candidates if isinstance(stage, str)]

    workflow_type = (metadata.get("workflow_type") or workflow.get("workflow_type") or "custom").lower()
    try:
        recipe = load_recipe(workflow_type)
    except FileNotFoundError:
        try:
            recipe = load_recipe("custom")
        except FileNotFoundError:
            return sorted(CANONICAL_STAGES)
    return [stage for stage in recipe.get("stages", []) if isinstance(stage, str)]


def _artifact_path_status(root: Path, artifact: dict[str, Any]) -> dict[str, Any] | None:
    path_value = artifact.get("path")
    if not path_value:
        return None
    path = Path(path_value)
    full_path = path if path.is_absolute() else root / path
    return {
        "artifact_id": artifact.get("artifact_id"),
        "name": artifact.get("name"),
        "path": path_value,
        "exists": full_path.exists(),
    }


def _artifact_summary(root: Path, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    by_stage: dict[str, int] = {}
    by_type: dict[str, int] = {}
    missing_paths = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        by_stage[artifact.get("stage", "unknown")] = by_stage.get(artifact.get("stage", "unknown"), 0) + 1
        by_type[artifact.get("type", "unknown")] = by_type.get(artifact.get("type", "unknown"), 0) + 1
        path_status = _artifact_path_status(root, artifact)
        if path_status and not path_status["exists"]:
            missing_paths.append(path_status)
    return {
        "total": len([artifact for artifact in artifacts if isinstance(artifact, dict)]),
        "by_stage": by_stage,
        "by_type": by_type,
        "missing_paths": missing_paths,
    }


def _stage_progress(
    stages: list[str],
    stage_registry: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_counts: dict[str, int] = {}
    for artifact in artifacts:
        if isinstance(artifact, dict):
            stage = artifact.get("stage", "unknown")
            artifact_counts[stage] = artifact_counts.get(stage, 0) + 1

    ordered = []
    seen = set()
    for stage in stages:
        entry = _as_dict(stage_registry.get(stage))
        ordered.append({
            "stage": stage,
            "status": entry.get("status", "pending"),
            "artifact_count": artifact_counts.get(stage, 0),
            "checkpoint_id": entry.get("checkpoint_id"),
            "started_at": entry.get("started_at"),
            "completed_at": entry.get("completed_at"),
        })
        seen.add(stage)

    for stage, entry_value in sorted(stage_registry.items()):
        if stage in seen:
            continue
        entry = _as_dict(entry_value)
        ordered.append({
            "stage": stage,
            "status": entry.get("status", "unknown"),
            "artifact_count": artifact_counts.get(stage, 0),
            "checkpoint_id": entry.get("checkpoint_id"),
            "started_at": entry.get("started_at"),
            "completed_at": entry.get("completed_at"),
            "outside_stage_sequence": True,
        })
    return ordered


def _lineage_links(artifacts: list[dict[str, Any]], lineage_state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifact_ids = {artifact.get("artifact_id") for artifact in artifacts if isinstance(artifact, dict)}
    links_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    missing_parents: dict[tuple[str, str], dict[str, Any]] = {}

    for link in _as_list(lineage_state.get("links")):
        if not isinstance(link, dict):
            continue
        child = link.get("child_artifact_id")
        parent = link.get("parent_artifact_id")
        relationship = link.get("relationship", "derived_from")
        if not child or not parent:
            continue
        links_by_key[(child, parent, relationship)] = {
            "child_artifact_id": child,
            "parent_artifact_id": parent,
            "relationship": relationship,
            "stage": link.get("stage"),
        }
        if parent not in artifact_ids:
            missing_parents[(child, parent)] = {
                "child_artifact_id": child,
                "missing_parent_artifact_id": parent,
            }

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        child = artifact.get("artifact_id")
        lineage = _as_dict(artifact.get("lineage"))
        for parent in _as_list(lineage.get("parent_artifacts")):
            if not child or not parent:
                continue
            links_by_key.setdefault((child, parent, "derived_from"), {
                "child_artifact_id": child,
                "parent_artifact_id": parent,
                "relationship": "derived_from",
                "stage": artifact.get("stage"),
            })
            if parent not in artifact_ids:
                missing_parents[(child, parent)] = {
                    "child_artifact_id": child,
                    "missing_parent_artifact_id": parent,
                }

    return list(links_by_key.values()), list(missing_parents.values())


def _gate_summary(gates: dict[str, Any]) -> dict[str, Any]:
    decisions = _as_list(gates.get("decisions"))
    latest: dict[str, dict[str, Any]] = {}
    for gate_name, value in gates.items():
        if gate_name == "decisions" or not isinstance(value, dict):
            continue
        latest[gate_name] = {
            "latest_decision": value.get("latest_decision"),
            "latest_decision_id": value.get("latest_decision_id"),
            "latest_decision_at": value.get("latest_decision_at"),
            "latest_agent": value.get("latest_agent"),
        }
    return {
        "decisions_count": len(decisions),
        "latest_decisions": latest,
    }


def _risks(
    workflow: dict[str, Any],
    stage_progress: list[dict[str, Any]],
    artifact_summary: dict[str, Any],
    checkpoints: list[Any],
    missing_parents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    risks = []
    if not workflow:
        risks.append({"code": "missing_workflow_state", "severity": "high", "message": "No workflow state is recorded."})
    if not checkpoints:
        risks.append({"code": "missing_checkpoint", "severity": "medium", "message": "No checkpoints are recorded."})
    failed = [stage["stage"] for stage in stage_progress if stage.get("status") == "failed"]
    if failed:
        risks.append({"code": "failed_stages", "severity": "high", "message": f"Failed stages: {', '.join(failed)}", "stages": failed})
    if artifact_summary["missing_paths"]:
        risks.append({
            "code": "missing_artifact_paths",
            "severity": "medium",
            "message": f"{len(artifact_summary['missing_paths'])} artifact path(s) are missing.",
            "artifacts": artifact_summary["missing_paths"],
        })
    if missing_parents:
        risks.append({
            "code": "missing_lineage_parents",
            "severity": "medium",
            "message": f"{len(missing_parents)} lineage parent reference(s) are missing.",
            "lineage": missing_parents,
        })
    return risks


def _next_actions(stage_progress: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = next((stage for stage in stage_progress if stage.get("status") == "failed"), None)
    if failed:
        return [{"action": "retry_stage", "stage": failed["stage"], "reason": "stage_failed"}]
    in_progress = next((stage for stage in stage_progress if stage.get("status") == "in_progress"), None)
    if in_progress:
        return [{"action": "continue_stage", "stage": in_progress["stage"], "reason": "stage_in_progress"}]
    pending = next((stage for stage in stage_progress if stage.get("status", "pending") == "pending"), None)
    if pending:
        return [{"action": "start_stage", "stage": pending["stage"], "reason": "stage_pending"}]
    return [{"action": "workflow_complete", "stage": None, "reason": "no_pending_stages"}]


def build_evidence_graph(
    project_root: str,
    *,
    stage: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    """Build a read-only artifact lineage graph for a project."""
    root = resolve_project_root(project_root=project_root)
    state = _read_project_state(root)
    artifacts = [artifact for artifact in state["artifacts"] if isinstance(artifact, dict)]
    all_links, missing_parents = _lineage_links(artifacts, state["lineage"])

    selected_ids = {artifact.get("artifact_id") for artifact in artifacts}
    if stage:
        selected_ids = {artifact.get("artifact_id") for artifact in artifacts if artifact.get("stage") == stage}
    if artifact_id:
        related_ids = {artifact_id}
        for link in all_links:
            if link["child_artifact_id"] == artifact_id:
                related_ids.add(link["parent_artifact_id"])
            if link["parent_artifact_id"] == artifact_id:
                related_ids.add(link["child_artifact_id"])
        selected_ids = related_ids if not stage else selected_ids.intersection(related_ids)

    nodes = []
    for artifact in artifacts:
        if artifact.get("artifact_id") not in selected_ids:
            continue
        path_status = _artifact_path_status(root, artifact)
        nodes.append({
            "artifact_id": artifact.get("artifact_id"),
            "name": artifact.get("name"),
            "type": artifact.get("type"),
            "stage": artifact.get("stage"),
            "version": artifact.get("version"),
            "path": artifact.get("path"),
            "checksum": artifact.get("checksum"),
            "path_exists": None if path_status is None else path_status["exists"],
        })

    links = [
        link for link in all_links
        if link["child_artifact_id"] in selected_ids and link["parent_artifact_id"] in selected_ids
    ]
    filtered_missing = [
        item for item in missing_parents
        if item["child_artifact_id"] in selected_ids
    ]
    return {
        "status": "success",
        "project_root": str(root),
        "filters": {"stage": stage, "artifact_id": artifact_id},
        "nodes": nodes,
        "links": links,
        "missing_parents": filtered_missing,
    }


def build_project_status(project_root: str) -> dict[str, Any]:
    """Build a read-only project status summary from SimFlow state."""
    root = resolve_project_root(project_root=project_root)
    state = _read_project_state(root)
    workflow = state["workflow"]
    metadata = state["metadata"]
    stages = _stage_sequence(workflow, metadata)
    stage_progress = _stage_progress(stages, state["stages"], state["artifacts"])
    artifact_summary = _artifact_summary(root, state["artifacts"])
    graph = build_evidence_graph(str(root))
    risks = _risks(workflow, stage_progress, artifact_summary, state["checkpoints"], graph["missing_parents"])

    completed = [item for item in stage_progress if item.get("status") == "completed"]
    return {
        "status": "success",
        "project_root": str(root),
        "workflow": {
            "workflow_id": workflow.get("workflow_id") or metadata.get("workflow_id"),
            "workflow_type": workflow.get("workflow_type") or metadata.get("workflow_type"),
            "status": workflow.get("status", "missing"),
            "current_stage": workflow.get("current_stage") or metadata.get("current_stage"),
            "entry_point": workflow.get("entry_point") or metadata.get("entry_point"),
        },
        "progress": {
            "total_stages": len(stages),
            "completed_stages": [item["stage"] for item in completed],
            "progress_pct": round(len(completed) / max(len(stages), 1) * 100, 1),
            "stages": stage_progress,
        },
        "artifacts": artifact_summary,
        "lineage": {
            "node_count": len(graph["nodes"]),
            "link_count": len(graph["links"]),
            "missing_parents": graph["missing_parents"],
        },
        "checkpoints": {
            "count": len(state["checkpoints"]),
            "latest": state["checkpoints"][-1] if state["checkpoints"] else None,
        },
        "gates": _gate_summary(state["gates"]),
        "verification": state["verification"],
        "risks": risks,
        "next_actions": _next_actions(stage_progress),
    }


def build_handoff_summary(project_root: str) -> dict[str, Any]:
    """Build a compact read-only handoff summary for agent/session transfer."""
    project_status = build_project_status(project_root)
    workflow = project_status["workflow"]
    progress = project_status["progress"]
    return {
        "status": "success",
        "project_root": project_status["project_root"],
        "workflow": workflow,
        "current_stage": workflow.get("current_stage"),
        "completed_stages": progress["completed_stages"],
        "latest_checkpoint": project_status["checkpoints"]["latest"],
        "artifact_summary": project_status["artifacts"],
        "risks": project_status["risks"],
        "next_actions": project_status["next_actions"],
        "gate_summary": project_status["gates"],
    }
