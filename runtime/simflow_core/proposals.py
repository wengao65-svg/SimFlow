"""Load and normalize proposal-stage artifacts for downstream workflow stages."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .artifacts import list_artifacts
from .state import read_state


REQUIRED_PROPOSAL_ARTIFACTS = ("proposal.md", "parameter_table.csv", "research_questions.json")
OPTIONAL_PROPOSAL_ARTIFACTS = ("proposal_contract.json", "protocol_contract.json")
SUPPORTED_SOFTWARE = {"vasp", "cp2k", "lammps"}
TRACKED_ONLY_SOFTWARE = {
    "gpumd",
    "nep",
    "neptrainkit",
    "deepmd",
    "dpgen",
    "mace",
    "nequip",
    "allegro",
    "ase",
    "custom",
}
MLP_MD_WORKFLOW_TYPES = {"mlp_md"}
CORE_PARAMETER_KEYS = {"workflow_type", "software", "material", "toolchain", "software_stack"}
CANONICAL_STAGE_SEQUENCE = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]
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
    known_names = {*REQUIRED_PROPOSAL_ARTIFACTS, *OPTIONAL_PROPOSAL_ARTIFACTS}
    by_name = {artifact.get("name"): artifact for artifact in artifacts if artifact.get("name") in known_names}
    missing = [name for name in REQUIRED_PROPOSAL_ARTIFACTS if name not in by_name]
    if missing:
        raise FileNotFoundError(f"Missing proposal artifacts: {', '.join(missing)}")
    return by_name


def _stage_index(stage: str | None) -> int:
    if stage in CANONICAL_STAGE_SEQUENCE:
        return CANONICAL_STAGE_SEQUENCE.index(stage)
    return 0


def _allows_direct_contract(metadata: dict[str, Any], minimum_stage: str) -> bool:
    entry_stage = metadata.get("entry_point")
    current_stage = metadata.get("current_stage")
    return max(_stage_index(entry_stage), _stage_index(current_stage)) >= _stage_index(minimum_stage)


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


def _normalize_tool_name(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _coerce_toolchain(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value.replace(";", ",").split(",")
        return [_normalize_tool_name(item) for item in _coerce_toolchain(parsed)]
    if isinstance(value, dict):
        raw_tools = value.get("tools") or value.get("software") or value.get("stack") or []
        return _coerce_toolchain(raw_tools)
    if isinstance(value, (list, tuple, set)):
        tools = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("software") or item.get("tool")
                if name:
                    tools.append(_normalize_tool_name(name))
            else:
                tools.append(_normalize_tool_name(item))
        return [tool for tool in tools if tool]
    return [_normalize_tool_name(value)]


def _extract_toolchain(metadata: dict[str, Any], parameter_values: dict[str, Any]) -> list[str]:
    tools: list[str] = []
    for value in (
        metadata.get("toolchain"),
        metadata.get("software_stack"),
        parameter_values.get("toolchain"),
        parameter_values.get("software_stack"),
    ):
        tools.extend(_coerce_toolchain(value))
    software = _normalize_tool_name(metadata.get("software") or parameter_values.get("software") or "")
    if software and software != "custom":
        tools.insert(0, software)
    seen: set[str] = set()
    return [tool for tool in tools if tool and not (tool in seen or seen.add(tool))]


def _software_support(toolchain: list[str]) -> dict[str, Any]:
    builtin = [tool for tool in toolchain if tool in SUPPORTED_SOFTWARE]
    tracked_only = [
        tool
        for tool in toolchain
        if tool not in SUPPORTED_SOFTWARE and tool in TRACKED_ONLY_SOFTWARE
    ]
    unknown = [
        tool
        for tool in toolchain
        if tool not in SUPPORTED_SOFTWARE and tool not in TRACKED_ONLY_SOFTWARE
    ]
    return {
        "builtin_helpers": builtin,
        "tracked_only": tracked_only,
        "unknown": unknown,
        "policy": "Only builtin helper software has SimFlow helper support; tracked-only tools are recorded for provenance and handoff.",
    }


def _resolve_primary_software(
    metadata: dict[str, Any],
    parameter_values: dict[str, Any],
) -> tuple[str, list[str], dict[str, Any]]:
    workflow_type = _normalize_tool_name(metadata.get("workflow_type") or parameter_values.get("workflow_type") or "dft")
    requested = _normalize_tool_name(metadata.get("software") or parameter_values.get("software") or "vasp")
    toolchain = _extract_toolchain(metadata, parameter_values)
    support = _software_support(toolchain)

    if requested in SUPPORTED_SOFTWARE:
        return requested, toolchain, support
    if workflow_type in MLP_MD_WORKFLOW_TYPES and requested in TRACKED_ONLY_SOFTWARE:
        support["requested_software"] = requested
        support["primary_software_normalized_from"] = requested
        return "custom", toolchain or [requested], support
    raise ValueError(f"Unsupported software for Milestone C: {requested or 'unknown'}")


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


def _load_optional_json(project_root: Path, artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not artifact:
        return {}
    path = resolve_artifact_path(project_root, artifact["path"])
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _metadata_parameter_rows(metadata: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        {
            "parameter": "workflow_type",
            "value": str(metadata.get("workflow_type", "dft")),
            "source": "metadata",
            "notes": "Direct entry metadata.",
        },
        {
            "parameter": "software",
            "value": str(metadata.get("software", "vasp")),
            "source": "metadata",
            "notes": "Direct entry metadata.",
        },
        {
            "parameter": "material",
            "value": str(metadata.get("material", "Not specified")),
            "source": "metadata",
            "notes": "Direct entry metadata.",
        },
    ]
    for key in ("toolchain", "software_stack"):
        if key in metadata and metadata.get(key) not in (None, "", [], {}):
            value = metadata[key]
            rows.append({
                "parameter": key,
                "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value),
                "source": "metadata",
                "notes": "Direct entry software/toolchain metadata.",
            })
    for key, value in metadata.get("parameters", {}).items():
        rows.append({
            "parameter": key,
            "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value),
            "source": "metadata.parameters",
            "notes": "User-provided direct entry parameter.",
        })
    return rows


def _build_direct_entry_contract(metadata: dict[str, Any]) -> dict[str, Any]:
    workflow_type = str(metadata.get("workflow_type") or "dft")
    material = metadata.get("material") or "Not specified"
    research_goal = metadata.get("research_goal") or ""
    parameter_values = metadata.get("parameters", {})
    software, toolchain, support = _resolve_primary_software(metadata, parameter_values)
    parameter_overrides = {key: value for key, value in parameter_values.items() if key not in CORE_PARAMETER_KEYS}
    task = _select_task(parameter_overrides)
    research_questions = [{
        "question_id": "rq_001",
        "category": "goal",
        "priority": "primary",
        "question": f"How should {research_goal or 'the current research goal'} be investigated for {material} using {software}?",
        "source": "metadata.research_goal",
    }]
    direct_contract = {
        "source": "direct_entry_metadata",
        "literature_evidence_summary": {
            "status": "not_provided",
            "artifact_ids": [],
            "summary_points": [],
            "open_questions": ["No proposal artifacts were registered before this direct stage entry."],
        },
        "risk_register": [{
            "risk_id": "risk_direct_entry_001",
            "risk": "No registered proposal artifacts were available for this direct stage entry.",
            "mitigation": "Keep generated model artifacts linked to direct user inputs and avoid evidence-backed proposal claims.",
            "severity": "medium",
        }],
        "resource_assumptions": {
            "real_submit": False,
            "dry_run_first": True,
            "resource_estimate_status": "direct_entry_unestimated",
        },
    }
    return {
        "workflow_type": workflow_type,
        "software": software,
        "material": material,
        "research_goal": research_goal,
        "task": task,
        "job_type": task,
        "structure_hints": _extract_structure_hints(parameter_overrides, metadata),
        "parameter_overrides": parameter_overrides,
        "parameter_rows": _metadata_parameter_rows(metadata),
        "toolchain": toolchain,
        "software_support": support,
        "research_questions": research_questions,
        "decision_criteria": [],
        "risk_register": direct_contract["risk_register"],
        "resource_assumptions": direct_contract["resource_assumptions"],
        "source_artifact_ids": [],
        "literature_evidence_summary": direct_contract["literature_evidence_summary"],
        "calculation_plan": {},
        "proposal_contract": direct_contract,
        "protocol_contract": {},
        "proposal_markdown": "",
        "proposal_artifacts": {},
        "direct_entry": True,
        "output_roots": {
            "plans": ".simflow/plans",
            "artifacts": ".simflow/artifacts",
            "reports": ".simflow/reports",
            "checkpoints": ".simflow/checkpoints",
            "state": ".simflow/state",
        },
    }


def load_proposal_contract(workflow_dir: str, *, allow_direct_entry: bool = False) -> dict[str, Any]:
    """Load proposal artifacts and normalize them into a downstream contract."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    metadata_state = read_state(project_root=str(project_root), state_file="metadata.json")

    try:
        artifacts = _load_required_artifacts(project_root)
    except FileNotFoundError:
        if allow_direct_entry and _allows_direct_contract(metadata_state, "modeling"):
            return _build_direct_entry_contract(metadata_state)
        raise

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
    proposal_contract = _load_optional_json(project_root, artifacts.get("proposal_contract.json"))
    protocol_contract = _load_optional_json(project_root, artifacts.get("protocol_contract.json"))

    workflow_type = str(metadata_state.get("workflow_type") or parameter_values.get("workflow_type") or "dft")
    software, toolchain, support = _resolve_primary_software(metadata_state, parameter_values)
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
        "toolchain": toolchain,
        "software_support": support,
        "research_questions": research_questions,
        "decision_criteria": proposal_contract.get("decision_criteria", []),
        "risk_register": proposal_contract.get("risk_register", []),
        "resource_assumptions": proposal_contract.get("resource_assumptions", {}),
        "source_artifact_ids": proposal_contract.get("source_artifact_ids", []),
        "literature_evidence_summary": proposal_contract.get("literature_evidence_summary", {}),
        "calculation_plan": proposal_contract.get("calculation_plan", {}),
        "proposal_contract": proposal_contract,
        "protocol_contract": protocol_contract,
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
