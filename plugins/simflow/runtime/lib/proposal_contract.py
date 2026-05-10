"""Load and normalize proposal-stage artifacts for downstream workflow stages."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .artifact import list_artifacts
from .state import read_state


REQUIRED_PROPOSAL_ARTIFACTS = ("proposal.md", "parameter_table.csv", "research_questions.json")
SUPPORTED_SOFTWARE = {"vasp", "cp2k"}
CORE_PARAMETER_KEYS = {"workflow_type", "software", "material"}
TASK_KEYS = ("task", "job_type", "calculation", "calc_type", "task_type")
STRUCTURE_HINT_KEYS = {
    "structure_file",
    "structure_path",
    "structure_type",
    "structure_source",
    "cif",
    "poscar",
    "lattice_param",
    "lattice_a",
    "lattice_b",
    "lattice_c",
    "a",
    "b",
    "c",
    "alpha",
    "beta",
    "gamma",
    "elements",
    "coords",
    "supercell",
    "surface",
    "miller_index",
    "adsorbate",
    "vacancy",
    "defect",
}


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def resolve_artifact_path(project_root: Path, artifact_path: str) -> Path:
    """Resolve a registry artifact path against the project root."""
    path = Path(artifact_path).expanduser()
    return path if path.is_absolute() else project_root / path


def _load_required_artifacts(project_root: Path) -> dict[str, dict[str, Any]]:
    artifacts = list_artifacts(stage="proposal", project_root=str(project_root))
    by_name = {artifact.get("name"): artifact for artifact in artifacts if artifact.get("name") in REQUIRED_PROPOSAL_ARTIFACTS}
    missing = [name for name in REQUIRED_PROPOSAL_ARTIFACTS if name not in by_name]
    if missing:
        raise FileNotFoundError(f"Missing proposal artifacts: {', '.join(missing)}")
    return by_name


def _read_parameter_rows(parameter_table_path: Path) -> list[dict[str, str]]:
    with parameter_table_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_parameter_value(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _parameter_values(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        row["parameter"]: _parse_parameter_value(row.get("value", ""))
        for row in rows
        if row.get("parameter")
    }


def _normalize_questions(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw_questions = payload.get("questions", [])
    elif isinstance(payload, list):
        raw_questions = payload
    else:
        raw_questions = []

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_questions, start=1):
        if isinstance(item, dict):
            question = str(item.get("question", "")).strip()
            if not question:
                continue
            normalized.append({
                "question_id": item.get("question_id") or f"rq_{index:03d}",
                "category": item.get("category") or "unspecified",
                "priority": item.get("priority") or "secondary",
                "question": question,
                "source": item.get("source") or "research_questions.json",
                **({"parameter_keys": item.get("parameter_keys")} if item.get("parameter_keys") else {}),
            })
            continue
        question = str(item).strip()
        if question:
            normalized.append({
                "question_id": f"rq_{index:03d}",
                "category": "unspecified",
                "priority": "secondary",
                "question": question,
                "source": "research_questions.json",
            })
    return normalized


def _select_task(parameter_overrides: dict[str, Any]) -> Any:
    for key in TASK_KEYS:
        if key in parameter_overrides and parameter_overrides[key] not in (None, ""):
            return parameter_overrides[key]
    return None


def _extract_structure_hints(parameter_overrides: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    hints = {key: value for key, value in parameter_overrides.items() if key in STRUCTURE_HINT_KEYS}
    material = metadata.get("material")
    if material:
        hints.setdefault("material", material)
    return hints


def load_proposal_contract(workflow_dir: str) -> dict[str, Any]:
    """Load proposal artifacts and normalize them into a downstream contract."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    metadata_state = read_state(project_root=str(project_root), state_file="metadata.json")

    artifacts = _load_required_artifacts(project_root)

    proposal_path = resolve_artifact_path(project_root, artifacts["proposal.md"]["path"])
    parameter_table_path = resolve_artifact_path(project_root, artifacts["parameter_table.csv"]["path"])
    research_questions_path = resolve_artifact_path(project_root, artifacts["research_questions.json"]["path"])

    for path in (proposal_path, parameter_table_path, research_questions_path):
        if not path.is_file():
            raise FileNotFoundError(f"Proposal artifact file not found: {path}")

    proposal_markdown = proposal_path.read_text(encoding="utf-8")
    parameter_rows = _read_parameter_rows(parameter_table_path)
    parameter_values = _parameter_values(parameter_rows)
    parameter_overrides = {key: value for key, value in parameter_values.items() if key not in CORE_PARAMETER_KEYS}
    research_questions_payload = json.loads(research_questions_path.read_text(encoding="utf-8"))
    research_questions = _normalize_questions(research_questions_payload)

    software = str(metadata_state.get("software") or parameter_values.get("software") or "").lower()
    if software not in SUPPORTED_SOFTWARE:
        raise ValueError(f"Unsupported software for Milestone C: {software or 'unknown'}")

    workflow_type = str(metadata_state.get("workflow_type") or parameter_values.get("workflow_type") or "dft")
    material = metadata_state.get("material") or parameter_values.get("material") or "Not specified"
    task = _select_task(parameter_overrides)

    return {
        "workflow_type": workflow_type,
        "software": software,
        "material": material,
        "research_goal": metadata_state.get("research_goal", ""),
        "task": task,
        "job_type": task,
        "structure_hints": _extract_structure_hints(parameter_overrides, metadata_state),
        "parameter_overrides": parameter_overrides,
        "parameter_rows": parameter_rows,
        "research_questions": research_questions,
        "proposal_markdown": proposal_markdown,
        "proposal_artifacts": {
            name: {
                "artifact_id": artifact["artifact_id"],
                "path": artifact["path"],
            }
            for name, artifact in artifacts.items()
        },
        "output_roots": {
            "plans": ".simflow/plans",
            "artifacts": ".simflow/artifacts",
            "reports": ".simflow/reports",
            "checkpoints": ".simflow/checkpoints",
            "state": ".simflow/state",
        },
    }
