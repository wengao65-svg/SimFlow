"""Deterministic project summary rebuild from canonical SimFlow sources."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .experiment_notebook import list_experiment_notebooks
from .records import list_project_records
from .state import resolve_project_root


PROJECT_SUMMARY_SCHEMA = "simflow.project.v2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _current_experiment(entries: list[dict[str, Any]]) -> dict[str, Any]:
    initial = entries[0]
    details = initial.get("details", {})
    status = initial.get("status", "active")
    scope_paths = list(details.get("scope_paths", []))
    title = details.get("title", initial.get("summary"))
    research_question = details.get("research_question")
    tags = list(details.get("tags", []))
    latest_observation = None
    latest_decision = None
    next_action = None
    attempts: set[str] = set()
    material: dict[str, dict[str, Any]] = {}

    for entry in entries:
        entry_details = entry.get("details", {})
        if entry.get("entry_type") == "experiment":
            if entry.get("status"):
                status = entry["status"]
            if entry.get("action") == "scope_update":
                scope_paths = list(entry_details.get("scope_paths", scope_paths))
                title = entry_details.get("title", title)
                research_question = entry_details.get("research_question", research_question)
                tags = list(entry_details.get("tags", tags))
        if entry.get("attempt_id"):
            attempts.add(entry["attempt_id"])
        if entry.get("entry_type") == "observation":
            latest_observation = entry["entry_id"]
        if entry.get("entry_type") == "decision":
            latest_decision = entry["entry_id"]
        if entry.get("next_action") is not None:
            next_action = entry["next_action"]
        if entry.get("entry_type") == "material_action":
            action_id = entry_details.get("material_action_id")
            if action_id:
                material[action_id] = entry

    open_material = [
        action_id for action_id, entry in material.items()
        if entry.get("status") == "planned"
    ]
    return {
        "experiment_id": initial["experiment_id"],
        "title": title,
        "research_question": research_question,
        "status": status,
        "scope_paths": scope_paths,
        "tags": tags,
        "attempt_ids": sorted(attempts),
        "entry_count": len(entries),
        "latest_entry_id": entries[-1]["entry_id"],
        "latest_entry_at": entries[-1]["created_at"],
        "latest_observation_id": latest_observation,
        "latest_decision_id": latest_decision,
        "open_material_action_ids": sorted(open_material),
        "next_action": next_action,
    }


def build_source_cursors(project_root: str) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    simflow = root / ".simflow"
    records = simflow / "records.jsonl"
    notebooks = simflow / "experiments"
    checkpoints = simflow / "checkpoints"
    return {
        "records": {
            "size_bytes": records.stat().st_size,
            "sha256": _sha256(records),
        } if records.is_file() else None,
        "notebooks": {
            path.name: {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(notebooks.glob("exp_*.md"))
        } if notebooks.is_dir() else {},
        "checkpoints": {
            path.name: {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(checkpoints.glob("*.json"))
        } if checkpoints.is_dir() else {},
    }


def build_project_summary(project_root: str) -> dict[str, Any]:
    """Build the current project view without writing it."""
    root = resolve_project_root(project_root=project_root)
    project_hash = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    notebooks = list_experiment_notebooks(str(root))
    experiments = [_current_experiment(item["entries"]) for item in notebooks]
    records = list_project_records(str(root))
    checkpoints_dir = root / ".simflow" / "checkpoints"
    checkpoint_paths = sorted(checkpoints_dir.glob("*.json")) if checkpoints_dir.is_dir() else []

    record_counts: dict[str, int] = {}
    active_run_ids: set[str] = set()
    latest_checkpoint_id = None
    latest_milestone_id = None
    latest_failure_id = None
    for record in records:
        kind = record.get("kind")
        record_counts[kind] = record_counts.get(kind, 0) + 1
        if kind == "milestone":
            latest_milestone_id = record.get("record_id")
        if kind == "failure":
            latest_failure_id = record.get("record_id")
        if kind == "checkpoint":
            latest_checkpoint_id = record.get("checkpoint_id")
        if kind == "run" and record.get("run_id"):
            if record.get("status") in {"planned", "prepared", "submitted", "queued", "running", "paused"}:
                active_run_ids.add(record["run_id"])
            elif record.get("status") in {"completed", "failed", "cancelled", "abandoned"}:
                active_run_ids.discard(record["run_id"])

    timestamps = [
        value for value in [
            *(item.get("latest_entry_at") for item in experiments),
            *(item.get("created_at") for item in records),
        ] if value
    ]
    active_experiments = [item["experiment_id"] for item in experiments if item["status"] == "active"]
    open_material = [
        {"experiment_id": item["experiment_id"], "material_action_id": action_id}
        for item in experiments for action_id in item["open_material_action_ids"]
    ]
    latest_experiment = max(experiments, key=lambda item: item["latest_entry_at"], default=None)
    latest_record = records[-1] if records else None
    summary = {
        "schema_version": PROJECT_SUMMARY_SCHEMA,
        "project_id": f"project_{project_hash}",
        "project_root": str(root),
        "created_at": min(timestamps) if timestamps else _now(),
        "updated_at": max(timestamps) if timestamps else _now(),
        "current": {
            "goal": latest_experiment.get("research_question") if latest_experiment else None,
            "active_experiment_ids": active_experiments,
            "latest_experiment_id": latest_experiment.get("experiment_id") if latest_experiment else None,
            "active_run_ids": sorted(active_run_ids),
            "active_run_id": sorted(active_run_ids)[-1] if active_run_ids else None,
            "latest_milestone_id": latest_milestone_id,
            "latest_failure_id": latest_failure_id,
            "latest_checkpoint_id": latest_checkpoint_id,
            "next_action": latest_experiment.get("next_action") if latest_experiment else None,
            "open_material_actions": open_material,
        },
        "counts": {
            "operational_total": len(records),
            "operational_by_kind": record_counts,
            "experiments": len(experiments),
            "experiment_entries": sum(item["entry_count"] for item in experiments),
            "checkpoints": len(checkpoint_paths),
        },
        "experiments": experiments,
        "last_record": {
            key: latest_record.get(key)
            for key in ("record_id", "kind", "status", "summary", "created_at")
            if latest_record and latest_record.get(key) is not None
        } if latest_record else None,
        "source_cursors": build_source_cursors(str(root)),
    }
    return summary


def _render_index(summary: dict[str, Any]) -> str:
    lines = ["# SimFlow Experiment Index", ""]
    if not summary["experiments"]:
        lines.append("No Experiment notebooks are recorded.")
        return "\n".join(lines) + "\n"
    for item in summary["experiments"]:
        lines.extend([
            f"## {item['title']}",
            "",
            f"- Experiment: `{item['experiment_id']}`",
            f"- Status: `{item['status']}`",
            f"- Research question: {item.get('research_question') or 'unspecified'}",
            f"- Notebook: `{item['experiment_id']}.md`",
            f"- Open material actions: {len(item['open_material_action_ids'])}",
            "",
        ])
    return "\n".join(lines)


def rebuild_project_summary(project_root: str, *, write: bool = True) -> dict[str, Any]:
    """Recompute project.json and the Experiment index from canonical sources."""
    root = resolve_project_root(project_root=project_root)
    summary = build_project_summary(str(root))
    if write:
        _write_atomic(
            root / ".simflow" / "project.json",
            json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        )
        _write_atomic(root / ".simflow" / "experiments" / "index.md", _render_index(summary))
    return summary


def project_summary_is_stale(project_root: str) -> bool:
    root = resolve_project_root(project_root=project_root)
    path = root / ".simflow" / "project.json"
    if not path.is_file():
        return True
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return True
    return current.get("source_cursors") != build_source_cursors(str(root))

