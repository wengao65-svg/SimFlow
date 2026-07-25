"""Deterministic audit and conservative repair of SimFlow workflow state."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .state import (
    CANONICAL_ARTIFACT_STAGE_DIRS,
    STATE_DIR,
    _backup_simflow_tree,
    _build_status_summary_md,
    read_state,
    resolve_project_root,
)


DEFAULT_MIN_CONFIDENCE = 0.81
KNOWN_PARTIAL_STATUSES = {
    "completed_with_review_pending",
    "completed_with_metadata_gaps",
    "candidate_package_ready_no_submit",
    "submit_ready",
    "submitted_running",
    "completed_ready_for_training",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_files(root: Path) -> dict[str, Path]:
    paths = {
        str(path.relative_to(root)): path
        for path in sorted((root / STATE_DIR).glob("*.json"))
        if path.is_file()
    }
    checkpoint_dir = root / ".simflow" / "checkpoints"
    if checkpoint_dir.exists():
        paths.update({
            str(path.relative_to(root)): path
            for path in sorted(checkpoint_dir.glob("*.json"))
            if path.is_file()
        })
    return paths


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_time(value: Any) -> float:
    if not value:
        return float("-inf")
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("-inf")


def _canonicalize_project_path(path: Any, root: Path) -> Optional[str]:
    if not isinstance(path, str) or not Path(path).is_absolute():
        return None
    old = Path(path)
    old_root = str(root)
    old_text = str(old)
    if not old_text.casefold().startswith(old_root.casefold().rstrip("/") + "/"):
        return None
    suffix = old_text[len(old_root):].lstrip("/")
    corrected = root / suffix
    if old_text != str(corrected) and corrected.exists():
        return str(corrected)
    return None


def _checkpoint_status(status: Any, complete_snapshot: bool) -> Optional[str]:
    normalized = str(status or "").strip().lower()
    if normalized == "failure":
        return "failure"
    if normalized == "partial":
        return "partial"
    if normalized == "success":
        return "success" if complete_snapshot else "partial"
    if normalized == "completed":
        return "success" if complete_snapshot else "partial"
    if normalized in KNOWN_PARTIAL_STATUSES:
        return "partial"
    return None


def _snapshot_is_recoverable(snapshot: Any, expected_workflow_id: str) -> bool:
    if not isinstance(snapshot, dict):
        return False
    workflow = snapshot.get("workflow.json")
    stages = snapshot.get("stages.json")
    return (
        isinstance(workflow, dict)
        and workflow.get("workflow_id") == expected_workflow_id
        and isinstance(stages, dict)
    )


def _finding(
    findings: list[dict[str, Any]],
    *,
    rule_id: str,
    confidence: float,
    target: str,
    before: Any,
    after: Any,
    reason: str,
    apply_policy: str = "auto",
) -> None:
    findings.append({
        "rule_id": rule_id,
        "confidence": confidence,
        "apply_policy": apply_policy,
        "target": target,
        "before": before,
        "after": after,
        "reason": reason,
    })


def _eligible(confidence: float, policy: str, threshold: float) -> bool:
    return policy == "auto" and confidence >= threshold


def _plan(project_root: str, min_confidence: float) -> tuple[dict[str, Any], dict[str, Any]]:
    if min_confidence <= 0.8:
        raise ValueError("min_confidence must be greater than 0.8")
    root = resolve_project_root(project_root=project_root)
    inspected_paths = _json_files(root)
    before_hashes = {name: _sha256(path) for name, path in inspected_paths.items()}
    originals = {name: _read_json(path, {}) for name, path in inspected_paths.items()}

    def state(name: str, default: Any) -> Any:
        key = f".simflow/state/{name}"
        if key not in originals:
            originals[key] = copy.deepcopy(default)
        return copy.deepcopy(originals[key])

    workflow = state("workflow.json", {})
    project = state("project.json", {})
    summary = state("summary.json", {})
    artifacts = state("artifacts.json", [])
    lineage = state("lineage.json", {"artifacts": [], "links": []})
    stages = state("stages.json", {})
    checkpoints = state("checkpoints.json", [])
    jobs = state("jobs.json", [])
    findings: list[dict[str, Any]] = []
    workflow_id = workflow.get("workflow_id")
    if not workflow_id:
        raise ValueError(
            "repair_state requires an initialized workflow with workflow_id; call init_workflow first"
        )
    project_workflow_id = project.get("workflow_id")
    identity_agrees = bool(workflow_id and (not project_workflow_id or project_workflow_id == workflow_id))
    repair_time = _now_iso()

    if project.get("project_root") != str(root):
        old_root = project.get("project_root")
        safe_case_change = isinstance(old_root, str) and old_root.casefold() == str(root).casefold()
        policy = "auto" if safe_case_change else "audit_only"
        confidence = 0.99 if safe_case_change else 0.4
        _finding(
            findings,
            rule_id="root.canonical_project_path",
            confidence=confidence,
            apply_policy=policy,
            target=".simflow/state/project.json#/project_root",
            before=old_root,
            after=str(root),
            reason="Use the caller-supplied canonical project root only for a case-equivalent path.",
        )
        if _eligible(confidence, policy, min_confidence):
            project["project_root"] = str(root)

    artifact_by_id: dict[str, dict[str, Any]] = {}
    observed_stages: set[str] = set()
    for index, artifact in enumerate(artifacts if isinstance(artifacts, list) else []):
        if not isinstance(artifact, dict) or not artifact.get("artifact_id"):
            continue
        artifact_id = artifact["artifact_id"]
        artifact_by_id[artifact_id] = artifact
        if artifact.get("stage") in CANONICAL_ARTIFACT_STAGE_DIRS:
            observed_stages.add(artifact["stage"])
        if not artifact.get("workflow_id") and identity_agrees:
            _finding(
                findings,
                rule_id="artifact.fill_workflow_id",
                confidence=0.99,
                target=f".simflow/state/artifacts.json#/{index}/workflow_id",
                before=None,
                after=workflow_id,
                reason="workflow.json and project.json identify one canonical workflow.",
            )
            if _eligible(0.99, "auto", min_confidence):
                artifact["workflow_id"] = workflow_id
        elif artifact.get("workflow_id") not in (None, workflow_id):
            _finding(
                findings,
                rule_id="artifact.conflicting_workflow_id",
                confidence=0.45,
                apply_policy="audit_only",
                target=f".simflow/state/artifacts.json#/{index}/workflow_id",
                before=artifact.get("workflow_id"),
                after=workflow_id,
                reason="Conflicting workflow provenance requires manual review.",
            )
        corrected = _canonicalize_project_path(artifact.get("path"), root)
        if corrected:
            _finding(
                findings,
                rule_id="root.live_path_prefix_case",
                confidence=0.97,
                target=f".simflow/state/artifacts.json#/{index}/path",
                before=artifact.get("path"),
                after=corrected,
                reason="The corrected case-preserving path exists under project_root.",
            )
            if _eligible(0.97, "auto", min_confidence):
                artifact["path"] = corrected

    if not isinstance(lineage, dict):
        lineage = {"artifacts": [], "links": []}
    nodes = lineage.get("artifacts") if isinstance(lineage.get("artifacts"), list) else []
    node_by_id = {
        node.get("artifact_id"): node
        for node in nodes
        if isinstance(node, dict) and node.get("artifact_id")
    }
    projection_fields = ("name", "type", "stage", "version", "path", "checksum")
    for artifact_id, artifact in artifact_by_id.items():
        node = node_by_id.get(artifact_id)
        if node is None:
            new_node = {
                "artifact_id": artifact_id,
                "workflow_id": artifact.get("workflow_id") or workflow_id,
                **{field: artifact.get(field) for field in projection_fields},
                "updated_at": repair_time,
            }
            _finding(
                findings,
                rule_id="lineage.create_missing_node",
                confidence=0.99,
                target=f".simflow/state/lineage.json#/artifacts/{len(nodes)}",
                before=None,
                after=new_node,
                reason="Reconstruct first-class lineage node from the registered artifact projection.",
            )
            if _eligible(0.99, "auto", min_confidence):
                nodes.append(new_node)
                node_by_id[artifact_id] = new_node
            continue
        if not node.get("workflow_id") and identity_agrees:
            _finding(
                findings,
                rule_id="lineage.fill_node_workflow_id",
                confidence=0.99,
                target=f".simflow/state/lineage.json#/artifacts/{nodes.index(node)}/workflow_id",
                before=None,
                after=workflow_id,
                reason="Node belongs to an artifact in the canonical workflow.",
            )
            if _eligible(0.99, "auto", min_confidence):
                node["workflow_id"] = workflow_id
        for field in projection_fields:
            expected = artifact.get(field)
            if node.get(field) != expected:
                _finding(
                    findings,
                    rule_id="lineage.sync_node_projection",
                    confidence=0.98,
                    target=f".simflow/state/lineage.json#/artifacts/{nodes.index(node)}/{field}",
                    before=node.get(field),
                    after=expected,
                    reason="Artifact registry is the canonical source for node projection fields.",
                )
                if _eligible(0.98, "auto", min_confidence):
                    node[field] = expected
                    node["updated_at"] = repair_time
    lineage["artifacts"] = nodes
    lineage.setdefault("links", [])

    known_ids = set(artifact_by_id)
    for link_index, link in enumerate(lineage.get("links", [])):
        if not isinstance(link, dict):
            continue
        parent = link.get("parent_artifact_id")
        if parent and parent not in known_ids:
            _finding(
                findings,
                rule_id="lineage.external_parent_reference",
                confidence=0.3,
                apply_policy="audit_only",
                target=f".simflow/state/lineage.json#/links/{link_index}/parent_artifact_id",
                before=parent,
                after=None,
                reason="Unknown parents are retained; creating or deleting provenance would be unsafe.",
            )

    checkpoint_files: dict[str, dict[str, Any]] = {}
    checkpoint_events: list[tuple[float, str, dict[str, Any]]] = []
    normalized_checkpoint_status: dict[str, str] = {}
    conflicted_checkpoint_ids: set[str] = set()
    for index, entry in enumerate(checkpoints if isinstance(checkpoints, list) else []):
        if not isinstance(entry, dict) or not entry.get("checkpoint_id"):
            continue
        checkpoint_id = entry["checkpoint_id"]
        rel_path = entry.get("path") or f".simflow/checkpoints/{checkpoint_id}.json"
        file_data = copy.deepcopy(originals.get(rel_path, {}))
        if rel_path in originals:
            checkpoint_files[rel_path] = file_data
        snapshot = file_data.get("state_snapshot") if isinstance(file_data, dict) else None
        complete = (
            entry.get("workflow_id") == workflow_id
            and _snapshot_is_recoverable(snapshot, workflow_id)
        )
        recoverable = bool(complete)
        original_status = entry.get("status")
        file_status = file_data.get("status") if isinstance(file_data, dict) and file_data else None
        status_conflict = file_status is not None and str(file_status) != str(original_status)
        normalized = None if status_conflict else _checkpoint_status(original_status, complete)
        if status_conflict:
            conflicted_checkpoint_ids.add(checkpoint_id)
            _finding(
                findings,
                rule_id="checkpoint.registry_file_status_conflict",
                confidence=0.2,
                apply_policy="audit_only",
                target=f".simflow/state/checkpoints.json#/{index}/status",
                before={"registry": original_status, "file": file_status},
                after=None,
                reason="Conflicting checkpoint status evidence cannot be resolved automatically.",
            )
        elif normalized is None:
            _finding(
                findings,
                rule_id="checkpoint.unknown_status",
                confidence=0.4,
                apply_policy="audit_only",
                target=f".simflow/state/checkpoints.json#/{index}/status",
                before=original_status,
                after=None,
                reason="Unknown historical status cannot be normalized safely.",
            )
        else:
            normalized_checkpoint_status[checkpoint_id] = normalized
            if original_status != normalized or entry.get("recoverable") != recoverable:
                _finding(
                    findings,
                    rule_id="checkpoint.sync_registry_file_metadata",
                    confidence=0.98,
                    target=f".simflow/state/checkpoints.json#/{index}",
                    before={"status": original_status, "recoverable": entry.get("recoverable")},
                    after={"status": normalized, "recoverable": recoverable},
                    reason="Normalize known status and derive recoverability from immutable snapshot structure.",
                )
                if _eligible(0.98, "auto", min_confidence):
                    if original_status != normalized:
                        entry["legacy_status"] = original_status
                    entry["status"] = normalized
                    entry["recoverable"] = recoverable
                    if isinstance(file_data, dict) and file_data:
                        file_status = file_data.get("status", original_status)
                        if file_status != normalized:
                            file_data["legacy_status"] = file_status
                        file_data["status"] = normalized
                        file_data["recoverable"] = recoverable
        stage_id = entry.get("stage_id")
        if stage_id in CANONICAL_ARTIFACT_STAGE_DIRS:
            observed_stages.add(stage_id)
            checkpoint_events.append((_parse_time(entry.get("created_at")), stage_id, entry))
        elif stage_id:
            _finding(
                findings,
                rule_id="checkpoint.custom_stage_id",
                confidence=0.45,
                apply_policy="audit_only",
                target=f".simflow/state/checkpoints.json#/{index}/stage_id",
                before=stage_id,
                after=None,
                reason="Historical activity labels are not promoted to top-level stages automatically.",
            )
        if entry.get("workflow_id") not in (None, workflow_id):
            _finding(
                findings,
                rule_id="checkpoint.adopt_legacy_workflow_id",
                confidence=0.65,
                apply_policy="audit_only",
                target=f".simflow/state/checkpoints.json#/{index}/workflow_id",
                before=entry.get("workflow_id"),
                after=workflow_id,
                reason="Historical workflow identities may be intentional and are preserved.",
            )

    if not isinstance(stages, dict):
        stages = {}
    for stage_name in sorted(observed_stages):
        if stage_name not in stages:
            new_stage = {
                "stage_name": stage_name,
                "status": "in_progress",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "failure_checkpoint_id": None,
                "last_success_checkpoint_id": None,
                "error_message": None,
                "error_report_artifact_id": None,
                "failure_id": None,
                "started_at": None,
                "completed_at": None,
            }
            _finding(
                findings,
                rule_id="stage.declare_canonical",
                confidence=0.96,
                target=f".simflow/state/stages.json#/{stage_name}",
                before=None,
                after=new_stage,
                reason="Canonical stage is referenced by registered artifacts or checkpoints.",
            )
            if _eligible(0.96, "auto", min_confidence):
                stages[stage_name] = new_stage

    for stage_name, stage_record in stages.items():
        if not isinstance(stage_record, dict):
            continue
        artifact_ids = [
            artifact_id for artifact_id, artifact in artifact_by_id.items()
            if artifact.get("stage") == stage_name
        ]
        old_outputs = list(stage_record.get("outputs", []))
        new_outputs = [*old_outputs, *[artifact_id for artifact_id in artifact_ids if artifact_id not in old_outputs]]
        if new_outputs != old_outputs:
            _finding(
                findings,
                rule_id="stage.sync_outputs",
                confidence=0.98,
                target=f".simflow/state/stages.json#/{stage_name}/outputs",
                before=old_outputs,
                after=new_outputs,
                reason="Append registered artifacts while preserving legacy output entries.",
            )
            if _eligible(0.98, "auto", min_confidence):
                stage_record["outputs"] = new_outputs
        matching = [
            entry for _, event_stage, entry in checkpoint_events
            if event_stage == stage_name
            and entry.get("workflow_id") == workflow_id
            and entry.get("checkpoint_id") not in conflicted_checkpoint_ids
        ]
        matching.sort(key=lambda entry: _parse_time(entry.get("created_at")))
        if matching:
            non_failure = [
                entry for entry in matching
                if normalized_checkpoint_status.get(entry["checkpoint_id"], entry.get("status")) != "failure"
            ]
            latest_id = non_failure[-1]["checkpoint_id"] if non_failure else None
            if latest_id and stage_record.get("checkpoint_id") != latest_id:
                _finding(
                    findings,
                    rule_id="stage.latest_checkpoint_ref",
                    confidence=0.92,
                    target=f".simflow/state/stages.json#/{stage_name}/checkpoint_id",
                    before=stage_record.get("checkpoint_id"),
                    after=latest_id,
                    reason="Reference the latest canonical-workflow checkpoint for this stage.",
                )
                if _eligible(0.92, "auto", min_confidence):
                    stage_record["checkpoint_id"] = latest_id
            failures = [
                entry for entry in matching
                if normalized_checkpoint_status.get(entry["checkpoint_id"], entry.get("status")) == "failure"
            ]
            if failures:
                failure_id = failures[-1]["checkpoint_id"]
                if stage_record.get("failure_checkpoint_id") != failure_id:
                    _finding(
                        findings,
                        rule_id="stage.latest_failure_checkpoint_ref",
                        confidence=0.98,
                        target=f".simflow/state/stages.json#/{stage_name}/failure_checkpoint_id",
                        before=stage_record.get("failure_checkpoint_id"),
                        after=failure_id,
                        reason="Failure checkpoints are tracked separately from normal recovery boundaries.",
                    )
                    if _eligible(0.98, "auto", min_confidence):
                        stage_record["failure_checkpoint_id"] = failure_id
            successful = [
                entry for entry in matching
                if normalized_checkpoint_status.get(entry["checkpoint_id"], entry.get("status")) == "success"
                and entry.get("recoverable", False)
            ]
            if successful:
                success_id = successful[-1]["checkpoint_id"]
                if stage_record.get("last_success_checkpoint_id") != success_id:
                    _finding(
                        findings,
                        rule_id="stage.latest_success_checkpoint_ref",
                        confidence=0.98,
                        target=f".simflow/state/stages.json#/{stage_name}/last_success_checkpoint_id",
                        before=stage_record.get("last_success_checkpoint_id"),
                        after=success_id,
                        reason="Reference the latest structurally recoverable success checkpoint.",
                    )
                    if _eligible(0.98, "auto", min_confidence):
                        stage_record["last_success_checkpoint_id"] = success_id

    activity_exists = bool(artifact_by_id or checkpoints or jobs)
    if workflow.get("status") == "initialized" and activity_exists:
        _finding(
            findings,
            rule_id="workflow.initialized_with_activity",
            confidence=0.98,
            target=".simflow/state/workflow.json#/status",
            before="initialized",
            after="in_progress",
            reason="Recorded artifacts, checkpoints, or jobs prove work has started.",
        )
        if _eligible(0.98, "auto", min_confidence):
            workflow["status"] = "in_progress"

    events = checkpoint_events + [
        (_parse_time(artifact.get("created_at")), artifact.get("stage"), artifact)
        for artifact in artifact_by_id.values()
        if artifact.get("stage") in CANONICAL_ARTIFACT_STAGE_DIRS
    ]
    events.sort(key=lambda item: item[0])
    if events and events[-1][0] != float("-inf"):
        latest_stage = events[-1][1]
        if workflow.get("current_stage") != latest_stage:
            _finding(
                findings,
                rule_id="workflow.latest_current_stage",
                confidence=0.92,
                target=".simflow/state/workflow.json#/current_stage",
                before=workflow.get("current_stage"),
                after=latest_stage,
                reason="Use the latest timestamped event carrying a canonical stage.",
            )
            if _eligible(0.92, "auto", min_confidence):
                workflow["current_stage"] = latest_stage

    if any(_eligible(item["confidence"], item["apply_policy"], min_confidence) for item in findings):
        workflow["updated_at"] = repair_time
        project["updated_at"] = repair_time
    rebuilt_summary = {
        **summary,
        "workflow_id": workflow.get("workflow_id"),
        "workflow_type": workflow.get("workflow_type"),
        "current_stage": workflow.get("current_stage"),
        "status": workflow.get("status"),
        "state_root": ".simflow",
        "summary_report": ".simflow/reports/status_summary.md",
        "created_at": summary.get("created_at") or workflow.get("created_at"),
        "updated_at": workflow.get("updated_at"),
    }
    if summary != rebuilt_summary:
        _finding(
            findings,
            rule_id="summary.rebuild",
            confidence=0.99,
            target=".simflow/state/summary.json",
            before=summary,
            after=rebuilt_summary,
            reason="Summary is a projection of canonical workflow state.",
        )
        if _eligible(0.99, "auto", min_confidence):
            summary = rebuilt_summary

    updates = {
        ".simflow/state/workflow.json": workflow,
        ".simflow/state/project.json": project,
        ".simflow/state/summary.json": summary,
        ".simflow/state/artifacts.json": artifacts,
        ".simflow/state/lineage.json": lineage,
        ".simflow/state/stages.json": stages,
        ".simflow/state/checkpoints.json": checkpoints,
        **checkpoint_files,
    }
    changed_updates = {
        name: data for name, data in updates.items()
        if originals.get(name) != data
    }
    findings.sort(key=lambda item: (item["rule_id"], item["target"]))
    report = {
        "mode": "audit",
        "project_root": str(root),
        "threshold": min_confidence,
        "generated_at": repair_time,
        "changed": bool(changed_updates),
        "eligible_findings": [
            item for item in findings
            if _eligible(item["confidence"], item["apply_policy"], min_confidence)
        ],
        "audit_only_findings": [
            item for item in findings if item["apply_policy"] != "auto"
        ],
        "all_findings": findings,
        "changed_files": sorted(changed_updates),
        "before_hashes": before_hashes,
        "backup_path": None,
        "report_path": None,
    }
    return report, changed_updates


def audit_state(project_root: str, *, min_confidence: float = DEFAULT_MIN_CONFIDENCE) -> dict[str, Any]:
    """Return a read-only repair plan."""
    report, _ = _plan(project_root, min_confidence)
    return report


def _write_json_temp(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        return temp
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def apply_state_repair(
    project_root: str,
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Back up and atomically apply eligible conservative state repairs."""
    report, updates = _plan(project_root, min_confidence)
    root = resolve_project_root(project_root=project_root)
    report["mode"] = "apply"
    report["run_id"] = "repair_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if not updates:
        report["changed"] = False
        report["after_hashes"] = report["before_hashes"]
        report["rollback_performed"] = False
        return report

    current_hashes = {
        name: _sha256(root / name)
        for name in report["before_hashes"]
        if (root / name).is_file()
    }
    if current_hashes != report["before_hashes"]:
        raise RuntimeError("state changed after repair planning; re-run audit/apply")

    backup = _backup_simflow_tree(root)
    report["backup_path"] = str(backup) if backup else None
    post_backup_hashes = {
        name: _sha256(root / name)
        for name in report["before_hashes"]
        if (root / name).is_file()
    }
    if post_backup_hashes != report["before_hashes"]:
        raise RuntimeError("state changed during repair backup; re-run audit/apply")
    previous = {
        name: (root / name).read_bytes() if (root / name).exists() else None
        for name in updates
    }
    temps: dict[str, Path] = {}
    replaced: list[str] = []
    status_path = root / ".simflow" / "reports" / "status_summary.md"
    report_dir = root / ".simflow" / "reports" / "repair_state"
    report_path = report_dir / f"{report['run_id']}.json"
    previous_status = status_path.read_bytes() if status_path.exists() else None
    try:
        for name, data in updates.items():
            temps[name] = _write_json_temp(root / name, data)
        for name in sorted(updates):
            current = (root / name).read_bytes() if (root / name).exists() else None
            if current != previous[name]:
                raise RuntimeError(f"state changed before replacing {name}; repair rolled back")
            os.replace(str(temps[name]), str(root / name))
            replaced.append(name)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_temp = status_path.with_name(f".{status_path.name}.{report['run_id']}.tmp")
        status_temp.write_text(_build_status_summary_md(root), encoding="utf-8")
        os.replace(str(status_temp), str(status_path))
        report_dir.mkdir(parents=True, exist_ok=True)
        report["report_path"] = str(report_path.relative_to(root))
        report["after_hashes"] = {
            name: _sha256(root / name)
            for name in sorted(set(report["before_hashes"]) | set(updates))
            if (root / name).is_file()
        }
        report["rollback_performed"] = False
        report_temp = _write_json_temp(report_path, report)
        os.replace(str(report_temp), str(report_path))
    except Exception:
        for temp in temps.values():
            temp.unlink(missing_ok=True)
        for name in reversed(replaced):
            path = root / name
            old = previous[name]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.rollback.", suffix=".tmp", dir=str(path.parent))
                with os.fdopen(fd, "wb") as handle:
                    handle.write(old)
                os.replace(temp_name, str(path))
        if previous_status is None:
            status_path.unlink(missing_ok=True)
        else:
            fd, temp_name = tempfile.mkstemp(prefix=".status_summary.rollback.", suffix=".tmp", dir=str(status_path.parent))
            with os.fdopen(fd, "wb") as handle:
                handle.write(previous_status)
            os.replace(temp_name, str(status_path))
        report_path.unlink(missing_ok=True)
        report["rollback_performed"] = True
        raise
    return report
