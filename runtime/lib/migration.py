"""Legacy workflow and project state migration helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .state import ensure_simflow_dir, resolve_project_root
from .workflow import canonical_stage_name, convert_legacy_workflow_to_recipe


LEGACY_WORKFLOW_TYPE_TO_RECIPE = {
    "dft": "dft",
    "aimd": "aimd",
    "md": "classical_md",
}


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _as_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def _as_list(payload: Any) -> list[Any]:
    return payload if isinstance(payload, list) else []


def _legacy_state_sources(root: Path) -> dict[str, dict[str, Any]]:
    simflow = root / ".simflow"
    sources = {
        "state_workflow": _as_dict(_read_json_if_exists(simflow / "state" / "workflow.json")),
        "workflow_state": _as_dict(_read_json_if_exists(simflow / "workflow_state.json")),
        "metadata": _as_dict(_read_json_if_exists(simflow / "metadata.json")),
    }
    return {name: payload for name, payload in sources.items() if payload}


def _first_value(sources: dict[str, dict[str, Any]], keys: list[str]) -> Any:
    for payload in sources.values():
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
    return None


def _canonical_recipe(workflow_type: Any) -> str:
    if not isinstance(workflow_type, str) or not workflow_type:
        return "custom"
    return LEGACY_WORKFLOW_TYPE_TO_RECIPE.get(workflow_type, workflow_type)


def _canonical_stage(stage: Any) -> Optional[str]:
    if not isinstance(stage, str) or not stage:
        return None
    return canonical_stage_name(stage)


def _legacy_files(root: Path) -> list[str]:
    simflow = root / ".simflow"
    candidates = [
        simflow / "metadata.json",
        simflow / "workflow_state.json",
        simflow / "artifacts.json",
        simflow / "checkpoints.json",
    ]
    existing = [str(path.relative_to(root)) for path in candidates if path.exists()]
    for path in sorted((simflow / "artifacts").glob("*.json")):
        existing.append(str(path.relative_to(root)))
    for path in sorted((simflow / "checkpoints").glob("*.json")):
        existing.append(str(path.relative_to(root)))
    return existing


def inspect_legacy_project(project_root: str) -> dict[str, Any]:
    """Inspect a project for legacy SimFlow state without modifying it."""
    root = resolve_project_root(project_root=project_root)
    sources = _legacy_state_sources(root)
    legacy_files = _legacy_files(root)
    workflow_type = _first_value(sources, ["workflow_type", "recipe", "type"])
    current_stage = _first_value(sources, ["current_stage", "stage", "entry_point"])
    canonical_current_stage = _canonical_stage(current_stage)
    recipe = _canonical_recipe(workflow_type)
    return {
        "project_root": str(root),
        "legacy_detected": bool(legacy_files),
        "legacy_files": legacy_files,
        "workflow_type": workflow_type,
        "recipe": recipe,
        "current_stage": current_stage,
        "canonical_current_stage": canonical_current_stage,
        "stage_map": {
            "literature": "literature_review",
            "review": "literature_review",
            "input_generation": "computation",
            "compute": "computation",
            "analysis": "analysis_visualization",
            "visualization": "analysis_visualization",
        },
    }


def _build_workflow_state(root: Path, sources: dict[str, dict[str, Any]], inspection: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    workflow_id = _first_value(sources, ["workflow_id"]) or f"wf_migrated_{int(datetime.now().timestamp())}"
    current_stage = inspection.get("canonical_current_stage") or "literature_review"
    workflow_type = inspection.get("workflow_type") or "custom"
    return {
        "workflow_id": workflow_id,
        "workflow_type": "custom",
        "recipe": inspection["recipe"],
        "tags": [tag for tag in [workflow_type, inspection["recipe"], "legacy_migrated"] if tag],
        "current_stage": current_stage,
        "status": "migrated",
        "entry_point": current_stage,
        "legacy_workflow_type": workflow_type,
        "legacy_state_files": inspection["legacy_files"],
        "created_at": _first_value(sources, ["created_at"]) or now,
        "updated_at": now,
        "migrated_at": now,
    }


def _stage_records(sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    raw_stages = _first_value(sources, ["stages"])
    raw_stage_states = _first_value(sources, ["stage_states"]) or {}
    records: dict[str, dict[str, Any]] = {}

    if isinstance(raw_stages, dict):
        iterable = raw_stages.items()
    elif isinstance(raw_stages, list):
        iterable = [(stage, {}) for stage in raw_stages]
    else:
        iterable = []

    for legacy_stage, payload in iterable:
        canonical = _canonical_stage(legacy_stage)
        if canonical is None:
            continue
        status = "pending"
        if isinstance(payload, dict):
            status = payload.get("status", status)
        if isinstance(raw_stage_states, dict):
            status = raw_stage_states.get(legacy_stage, status)
        records.setdefault(canonical, {
            "stage_name": canonical,
            "status": status,
            "legacy_stages": [],
            "inputs": [],
            "outputs": [],
            "checkpoint_id": None,
        })
        records[canonical]["legacy_stages"].append(legacy_stage)
    return records


def _migrate_metadata_records(root: Path, directory: str) -> list[dict[str, Any]]:
    records = []
    base = root / ".simflow" / directory
    for path in sorted(base.glob("*.json")):
        payload = _read_json_if_exists(path)
        if not isinstance(payload, dict):
            continue
        record = dict(payload)
        if isinstance(record.get("stage"), str):
            record["legacy_stage"] = record["stage"]
            record["stage"] = canonical_stage_name(record["stage"])
        record.setdefault("legacy_source", str(path.relative_to(root)))
        records.append(record)
    return records


def _copy_legacy_reports(root: Path) -> list[str]:
    copied = []
    reports_dir = root / ".simflow" / "reports"
    legacy_reports = reports_dir / "legacy"
    for path in sorted((root / ".simflow").glob("*.md")):
        legacy_reports.mkdir(parents=True, exist_ok=True)
        target = legacy_reports / path.name
        shutil.copy2(path, target)
        copied.append(str(target.relative_to(root)))
    return copied


def migrate_project_state(project_root: str) -> dict[str, Any]:
    """Migrate legacy .simflow state into canonical state files without deleting legacy files."""
    root = resolve_project_root(project_root=project_root)
    inspection = inspect_legacy_project(str(root))
    sources = _legacy_state_sources(root)
    ensure_simflow_dir(project_root=str(root))

    workflow_state = _build_workflow_state(root, sources, inspection)
    stage_records = _stage_records(sources)
    if workflow_state["current_stage"] not in stage_records:
        stage_records[workflow_state["current_stage"]] = {
            "stage_name": workflow_state["current_stage"],
            "status": "pending",
            "legacy_stages": [],
            "inputs": [],
            "outputs": [],
            "checkpoint_id": None,
        }

    artifacts = _migrate_metadata_records(root, "artifacts")
    checkpoints = _migrate_metadata_records(root, "checkpoints")
    copied_reports = _copy_legacy_reports(root)

    state_dir = root / ".simflow" / "state"
    _write_json(state_dir / "workflow.json", workflow_state)
    _write_json(state_dir / "stages.json", stage_records)
    if artifacts:
        _write_json(state_dir / "artifacts.json", artifacts)
    if checkpoints:
        _write_json(state_dir / "checkpoints.json", checkpoints)

    report = {
        "status": "success",
        "project_root": str(root),
        "recipe": workflow_state["recipe"],
        "current_stage": workflow_state["current_stage"],
        "legacy_files_preserved": inspection["legacy_files"],
        "legacy_reports_copied": copied_reports,
        "artifacts_migrated": len(artifacts),
        "checkpoints_migrated": len(checkpoints),
    }
    _write_json(root / ".simflow" / "reports" / "migration.json", report)
    (root / ".simflow" / "reports" / "migration.md").write_text(
        "\n".join([
            "# SimFlow Migration Report",
            "",
            f"- Status: {report['status']}",
            f"- Recipe: {report['recipe']}",
            f"- Current stage: {report['current_stage']}",
            f"- Legacy files preserved: {len(report['legacy_files_preserved'])}",
            f"- Artifacts migrated: {report['artifacts_migrated']}",
            f"- Checkpoints migrated: {report['checkpoints_migrated']}",
            "",
        ]),
        encoding="utf-8",
    )
    return report


def convert_workflow_file(input_path: str, output_path: Optional[str] = None) -> dict[str, Any]:
    """Convert one legacy workflow JSON file into a recipe dict and optionally write it."""
    source = Path(input_path).expanduser().resolve()
    workflow = _read_json(source)
    recipe = convert_legacy_workflow_to_recipe(workflow, source_path=source)
    if output_path:
        _write_json(Path(output_path).expanduser().resolve(), recipe)
    return recipe
