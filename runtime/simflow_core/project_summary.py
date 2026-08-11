"""Deterministic project summary rebuild from canonical SimFlow sources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .experiment_notebook import list_experiment_notebooks
from .records import list_project_records
from .state import resolve_project_path, resolve_project_root


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
    active_run_ids: list[str] = []
    latest_checkpoint_id = None
    latest_milestone_id = None
    latest_failure_id = None
    latest_goal = None
    latest_next_action = None
    for record in records:
        kind = record.get("kind")
        record_counts[kind] = record_counts.get(kind, 0) + 1
        if kind == "milestone":
            latest_milestone_id = record.get("record_id")
        if kind == "failure":
            latest_failure_id = record.get("record_id")
        if kind == "checkpoint":
            latest_checkpoint_id = record.get("checkpoint_id")
        if record.get("goal") is not None:
            latest_goal = record.get("goal")
        if record.get("next_action") is not None:
            latest_next_action = record.get("next_action")
        if kind == "run" and record.get("run_id"):
            if record.get("status") in {"planned", "prepared", "submitted", "queued", "running", "paused"}:
                if record["run_id"] in active_run_ids:
                    active_run_ids.remove(record["run_id"])
                active_run_ids.append(record["run_id"])
            elif record.get("status") in {"completed", "failed", "cancelled", "abandoned"}:
                if record["run_id"] in active_run_ids:
                    active_run_ids.remove(record["run_id"])

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
            "goal": latest_experiment.get("research_question") if latest_experiment else latest_goal,
            "active_experiment_ids": active_experiments,
            "latest_experiment_id": latest_experiment.get("experiment_id") if latest_experiment else None,
            "active_run_ids": active_run_ids,
            "active_run_id": active_run_ids[-1] if active_run_ids else None,
            "latest_milestone_id": latest_milestone_id,
            "latest_failure_id": latest_failure_id,
            "latest_checkpoint_id": latest_checkpoint_id,
            "next_action": latest_experiment.get("next_action") if latest_experiment and latest_experiment.get("next_action") is not None else latest_next_action,
            "open_material_actions": open_material,
        },
        "counts": {
            "total": len(records),
            "by_kind": record_counts,
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


def inspect_experiment_context(
    project_root: str,
    *,
    working_directory: str | None = None,
    query: str | None = None,
    experiment_id: str | None = None,
    attempt_id: str | None = None,
    entry_type: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Rank relevant Experiments and merge scientific and operational timelines."""
    root = resolve_project_root(project_root=project_root)
    summary = build_project_summary(str(root))
    notebooks = {item["header"]["experiment_id"]: item for item in list_experiment_notebooks(str(root))}
    directory = resolve_project_path(working_directory or str(root), project_root=str(root))
    relative_directory = directory.relative_to(root).as_posix() or "."
    query_tokens = {
        token for token in re.findall(r"[A-Za-z0-9_+-]{3,}", str(query or "").lower())
    }

    candidates = []
    for item in summary["experiments"]:
        if experiment_id and item["experiment_id"] != experiment_id:
            continue
        path_match = False
        path_reasons = []
        for scope in item.get("scope_paths", []):
            scope_path = resolve_project_path(scope, project_root=str(root))
            try:
                directory.relative_to(scope_path)
                path_match = True
                path_reasons.append(f"working_directory is inside {scope}")
                continue
            except ValueError:
                pass
            try:
                scope_path.relative_to(directory)
                path_match = True
                path_reasons.append(f"scope {scope} is inside working_directory")
            except ValueError:
                pass
        haystack = " ".join([
            str(item.get("title") or ""),
            str(item.get("research_question") or ""),
            " ".join(item.get("tags", [])),
        ]).lower()
        matched_tokens = sorted(token for token in query_tokens if token in haystack)
        query_match = bool(matched_tokens)
        score = (100 if path_match else 0) + min(50, len(matched_tokens) * 5) + (10 if item["status"] == "active" else 0)
        reasons = [*path_reasons]
        if matched_tokens:
            reasons.append(f"query tokens matched: {', '.join(matched_tokens)}")
        if item["status"] == "active":
            reasons.append("experiment is active")
        candidates.append({
            **item,
            "score": score,
            "path_match": path_match,
            "query_match": query_match,
            "match_reasons": reasons,
        })
    candidates.sort(key=lambda item: (item["score"], item["latest_entry_at"]), reverse=True)

    selected_id = None
    if experiment_id and experiment_id in notebooks:
        selected_id = experiment_id
    else:
        active_path = [item for item in candidates if item["status"] == "active" and item["path_match"]]
        if len(active_path) == 1:
            selected_id = active_path[0]["experiment_id"]
        else:
            active_both = [item for item in active_path if item["query_match"]]
            if len(active_both) == 1:
                selected_id = active_both[0]["experiment_id"]

    entries: list[dict[str, Any]] = []
    if selected_id:
        entries = list(notebooks[selected_id]["entries"])
        if attempt_id:
            entries = [item for item in entries if item.get("attempt_id") == attempt_id]
        if entry_type:
            entries = [item for item in entries if item.get("entry_type") == entry_type]
    operational = [
        record for record in list_project_records(str(root))
        if selected_id and (
            record.get("experiment_id") == selected_id
            or (isinstance(record.get("details"), dict) and record["details"].get("experiment_id") == selected_id)
        )
    ]
    if attempt_id:
        operational = [
            record for record in operational
            if record.get("attempt_id") == attempt_id
            or (isinstance(record.get("details"), dict) and record["details"].get("attempt_id") == attempt_id)
        ]
    timeline = [
        *({"source": "notebook", **item} for item in entries),
        *({"source": "operational", **item} for item in operational),
    ]
    timeline.sort(key=lambda item: item.get("created_at", ""))
    bounded = max(1, min(int(limit), 200))
    return {
        "working_directory": relative_directory,
        "query": query,
        "candidates": candidates,
        "selected_experiment_id": selected_id,
        "selection_ambiguous": selected_id is None and len(candidates) > 1,
        "entries": entries[-bounded:],
        "operational_records": operational[-bounded:],
        "timeline": timeline[-bounded:],
    }


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
        experiments_dir = root / ".simflow" / "experiments"
        if summary["experiments"] or experiments_dir.is_dir():
            _write_atomic(experiments_dir / "index.md", _render_index(summary))
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
