"""Append-only Markdown notebooks for scientific Experiment memory."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .records import sanitize_record_value
from .state import resolve_project_path, resolve_project_root


EXPERIMENT_SCHEMA = "simflow.experiment_notebook.v1"
ENTRY_SCHEMA = "simflow.experiment_entry.v1"
EXPERIMENT_ENTRY_TYPES = {
    "experiment",
    "attempt",
    "observation",
    "decision",
    "material_action",
    "recovery",
}
EXPERIMENT_STATUSES = {"active", "paused", "completed", "abandoned", "superseded"}
MATERIAL_ACTION_STATUSES = {"planned", "completed", "partial", "failed", "reverted"}
MATERIAL_OPERATIONS = {
    "delete",
    "filter",
    "deduplicate",
    "overwrite",
    "truncate",
    "move",
    "replace_dataset",
    "clean_trajectory",
    "other_evidence_change",
}
RECOVERABILITY = {"reversible", "partially_reversible", "irreversible"}

_HEADER_RE = re.compile(r"<!-- simflow-experiment:v1\n(.*?)\n-->", re.DOTALL)
_ENTRY_RE = re.compile(r"<!-- simflow-entry:v1\n(.*?)\n-->", re.DOTALL)


class ExperimentNotebookError(ValueError):
    """Raised when an Experiment notebook request is invalid."""


class NotebookFormatError(ExperimentNotebookError):
    """Raised when an existing notebook cannot be parsed safely."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _experiment_dir(root: Path) -> Path:
    return root / ".simflow" / "experiments"


def experiment_notebook_path(project_root: str, experiment_id: str) -> Path:
    root = resolve_project_root(project_root=project_root)
    if not re.fullmatch(r"exp_[0-9a-f]{12}", str(experiment_id)):
        raise ExperimentNotebookError(f"Invalid experiment_id: {experiment_id}")
    return _experiment_dir(root) / f"{experiment_id}.md"


@contextmanager
def _locked_file(path: Path, mode: str) -> Iterator[Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8") as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        try:
            yield handle
        finally:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass


def _normalize_scope_paths(root: Path, values: list[str]) -> list[str]:
    if not values:
        raise ExperimentNotebookError("scope_paths must contain at least one project path")
    normalized = []
    for value in values:
        resolved = resolve_project_path(value, project_root=str(root))
        normalized.append(resolved.relative_to(root).as_posix() or ".")
    return sorted(set(normalized))


def _normalize_evidence(root: Path, values: list[Any] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in values or []:
        ref = {"path": raw} if isinstance(raw, str) else dict(raw)
        path_value = ref.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ExperimentNotebookError("Every evidence reference requires a path")
        resolved = resolve_project_path(path_value, project_root=str(root))
        restricted = bool(ref.get("restricted"))
        if restricted:
            ref["path"] = "[RESTRICTED PATH]"
            ref.setdefault("name", resolved.name)
        else:
            ref["path"] = resolved.relative_to(root).as_posix()
        ref["exists"] = resolved.exists()
        if resolved.is_file():
            ref.setdefault("sha256", _sha256(resolved))
            ref.setdefault("size_bytes", resolved.stat().st_size)
        normalized.append(sanitize_record_value(ref))
    return normalized


def _header(experiment_id: str, created_at: str) -> dict[str, Any]:
    return {
        "schema_version": EXPERIMENT_SCHEMA,
        "experiment_id": experiment_id,
        "created_at": created_at,
    }


def _render_header(header: dict[str, Any]) -> str:
    return (
        "<!-- simflow-experiment:v1\n"
        f"{_canonical_json(header)}\n"
        "-->\n"
        f"# Experiment {header['experiment_id']}\n\n"
        "This notebook is append-only. Structured metadata is stored in each "
        "SimFlow entry marker; evidence remains in the referenced project files.\n"
    )


def _render_entry(entry: dict[str, Any]) -> str:
    details = entry.get("details", {})
    evidence = entry.get("evidence", [])
    lines = [
        "<!-- simflow-entry:v1",
        _canonical_json(entry),
        "-->",
        f"## {entry['created_at']} | {entry['entry_type']} | {entry['action']}",
        "",
        f"**Summary:** {entry['summary']}",
    ]
    if details:
        lines.extend(["", "### Details", "", "```json", json.dumps(details, indent=2, ensure_ascii=False, sort_keys=True), "```"])
    if evidence:
        lines.extend(["", "### Evidence", ""])
        for ref in evidence:
            role = f" ({ref['role']})" if ref.get("role") else ""
            digest = f" sha256={ref['sha256']}" if ref.get("sha256") else ""
            lines.append(f"- `{ref.get('path', ref.get('name', 'restricted'))}`{role}{digest}")
    if entry.get("next_action") is not None:
        lines.extend(["", "### Next Action", "", json.dumps(entry["next_action"], ensure_ascii=False, sort_keys=True)])
    return "\n".join(lines) + "\n"


def _parse_payload(raw: str, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise NotebookFormatError(f"Invalid {label} JSON: {error}") from error
    if not isinstance(payload, dict):
        raise NotebookFormatError(f"{label} must be a JSON object")
    return payload


def parse_experiment_notebook(path: Path) -> dict[str, Any]:
    """Parse one canonical notebook without modifying it."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise NotebookFormatError(f"Cannot read notebook {path}: {error}") from error
    header_match = _HEADER_RE.search(text)
    if not header_match:
        raise NotebookFormatError(f"Notebook header is missing: {path}")
    header = _parse_payload(header_match.group(1), label="experiment header")
    if header.get("schema_version") != EXPERIMENT_SCHEMA:
        raise NotebookFormatError(f"Unsupported notebook schema in {path}")
    experiment_id = header.get("experiment_id")
    if path.name != f"{experiment_id}.md":
        raise NotebookFormatError(f"Notebook filename does not match experiment_id: {path}")

    entries = []
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    for match in _ENTRY_RE.finditer(text):
        entry = _parse_payload(match.group(1), label="experiment entry")
        if entry.get("schema_version") != ENTRY_SCHEMA:
            raise NotebookFormatError(f"Unsupported entry schema in {path}")
        if entry.get("experiment_id") != experiment_id:
            raise NotebookFormatError(f"Entry is bound to a different experiment in {path}")
        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str) or entry_id in seen_ids:
            raise NotebookFormatError(f"Duplicate or missing entry_id in {path}")
        seen_ids.add(entry_id)
        key = entry.get("idempotency_key")
        if key:
            if key in seen_keys:
                raise NotebookFormatError(f"Duplicate idempotency_key in {path}")
            seen_keys.add(key)
        entries.append(entry)
    if not entries or entries[0].get("entry_type") != "experiment" or entries[0].get("action") != "create":
        raise NotebookFormatError(f"Notebook lacks an initial experiment/create entry: {path}")
    return {"header": header, "entries": entries, "path": path}


def _validate_entry(entry: dict[str, Any], existing: list[dict[str, Any]]) -> None:
    entry_type = entry["entry_type"]
    if entry_type not in EXPERIMENT_ENTRY_TYPES:
        raise ExperimentNotebookError(f"Unsupported experiment entry_type: {entry_type}")
    if not entry["summary"].strip():
        raise ExperimentNotebookError("summary is required")
    if entry_type == "experiment" and entry.get("status") and entry["status"] not in EXPERIMENT_STATUSES:
        raise ExperimentNotebookError(f"Unsupported experiment status: {entry['status']}")
    if entry_type != "material_action":
        return

    status = entry.get("status")
    details = entry.get("details", {})
    if status not in MATERIAL_ACTION_STATUSES:
        raise ExperimentNotebookError("material_action requires a supported status")
    operation = details.get("operation")
    if operation not in MATERIAL_OPERATIONS:
        raise ExperimentNotebookError(
            "material_action operation must change persistent evidence or recoverability"
        )
    material_action_id = details.get("material_action_id")
    if not material_action_id:
        raise ExperimentNotebookError("material_action_id is required")
    if status == "planned":
        if not details.get("targets") or not details.get("reason"):
            raise ExperimentNotebookError("planned material_action requires targets and reason")
        if details.get("recoverability") not in RECOVERABILITY:
            raise ExperimentNotebookError("planned material_action requires recoverability")
        if any(
            item.get("entry_type") == "material_action"
            and item.get("details", {}).get("material_action_id") == material_action_id
            for item in existing
        ):
            raise ExperimentNotebookError(f"material_action_id already exists: {material_action_id}")
        return
    planned = [
        item for item in existing
        if item.get("entry_type") == "material_action"
        and item.get("status") == "planned"
        and item.get("details", {}).get("material_action_id") == material_action_id
    ]
    if not planned:
        raise ExperimentNotebookError("terminal material_action requires a matching planned entry")
    if not details.get("outcome"):
        raise ExperimentNotebookError("terminal material_action requires outcome")


def create_experiment(
    project_root: str,
    *,
    title: str,
    research_question: str,
    scope_paths: list[str],
    tags: list[str] | None = None,
    summary: str | None = None,
    experiment_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create one Experiment notebook and its immutable initial entry."""
    root = resolve_project_root(project_root=project_root)
    if not str(title).strip() or not str(research_question).strip():
        raise ExperimentNotebookError("title and research_question are required")
    experiment_id = experiment_id or _id("exp")
    path = experiment_notebook_path(str(root), experiment_id)
    if path.exists():
        existing = parse_experiment_notebook(path)
        if idempotency_key and existing["entries"][0].get("idempotency_key") == idempotency_key:
            return {"experiment_id": experiment_id, "entry": existing["entries"][0], "path": path, "idempotent_replay": True}
        raise ExperimentNotebookError(f"Experiment notebook already exists: {experiment_id}")

    created_at = _now()
    entry = {
        "schema_version": ENTRY_SCHEMA,
        "entry_id": _id("ent"),
        "experiment_id": experiment_id,
        "entry_type": "experiment",
        "action": "create",
        "status": "active",
        "summary": str(summary or title).strip(),
        "details": {
            "title": str(title).strip(),
            "research_question": str(research_question).strip(),
            "scope_paths": _normalize_scope_paths(root, scope_paths),
            "tags": sorted(set(str(item).strip() for item in (tags or []) if str(item).strip())),
        },
        "created_at": created_at,
    }
    if idempotency_key:
        entry["idempotency_key"] = str(idempotency_key)
    entry = sanitize_record_value(entry)
    content = _render_header(_header(experiment_id, created_at)) + "\n" + _render_entry(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _locked_file(path, "x") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise ExperimentNotebookError(f"Experiment notebook already exists: {experiment_id}") from error
    return {"experiment_id": experiment_id, "entry": entry, "path": path, "idempotent_replay": False}


def append_experiment_entry(
    project_root: str,
    *,
    experiment_id: str,
    entry_type: str,
    action: str,
    summary: str,
    status: str | None = None,
    attempt_id: str | None = None,
    parent_entry_ids: list[str] | None = None,
    runtime_record_ids: list[str] | None = None,
    evidence: list[Any] | None = None,
    details: dict[str, Any] | None = None,
    next_action: Any = None,
    idempotency_key: str | None = None,
    entry_id: str | None = None,
) -> dict[str, Any]:
    """Append one validated scientific entry to an existing notebook."""
    root = resolve_project_root(project_root=project_root)
    path = experiment_notebook_path(str(root), experiment_id)
    if not path.is_file():
        raise ExperimentNotebookError(f"Unknown experiment: {experiment_id}")
    with _locked_file(path, "r+") as handle:
        parsed = parse_experiment_notebook(path)
        if idempotency_key:
            for existing in parsed["entries"]:
                if existing.get("idempotency_key") == idempotency_key:
                    return {"entry": existing, "path": path, "idempotent_replay": True}
        normalized_details = sanitize_record_value(details or {})
        if entry_type == "material_action" and status == "planned":
            normalized_details.setdefault("material_action_id", _id("mat"))
        entry = {
            "schema_version": ENTRY_SCHEMA,
            "entry_id": entry_id or _id("ent"),
            "experiment_id": experiment_id,
            "entry_type": str(entry_type).strip(),
            "action": str(action).strip(),
            "summary": str(summary).strip(),
            "status": str(status).strip().lower() if status else None,
            "attempt_id": str(attempt_id) if attempt_id else None,
            "parent_entry_ids": list(parent_entry_ids or []),
            "runtime_record_ids": list(runtime_record_ids or []),
            "evidence": _normalize_evidence(root, evidence),
            "details": normalized_details,
            "next_action": sanitize_record_value(next_action),
            "idempotency_key": str(idempotency_key) if idempotency_key else None,
            "created_at": _now(),
        }
        entry = {key: value for key, value in entry.items() if value not in (None, [], {})}
        _validate_entry(entry, parsed["entries"])
        handle.seek(0, os.SEEK_END)
        handle.write("\n" + _render_entry(entry))
        handle.flush()
        os.fsync(handle.fileno())
    return {"entry": entry, "path": path, "idempotent_replay": False}


def list_experiment_notebooks(project_root: str) -> list[dict[str, Any]]:
    """Parse every canonical Experiment notebook under the project root."""
    root = resolve_project_root(project_root=project_root)
    directory = _experiment_dir(root)
    if not directory.is_dir():
        return []
    return [parse_experiment_notebook(path) for path in sorted(directory.glob("exp_*.md"))]

