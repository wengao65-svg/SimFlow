#!/usr/bin/env python3
"""Generate proposal artifacts from registered review outputs."""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.state import read_state


REQUIRED_REVIEW_ARTIFACTS = ("review_summary.md", "gap_analysis.md")
CANONICAL_STAGE_SEQUENCE = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def resolve_artifact_path(project_root: Path, artifact_path: str) -> Path:
    """Resolve a registry artifact path against the project root."""
    path = Path(artifact_path).expanduser()
    return path if path.is_absolute() else project_root / path


def load_review_artifacts(project_root: Path) -> tuple[dict[str, str], list[dict]]:
    """Load required review artifact contents from the canonical registry."""
    artifacts = list_artifacts(stage="literature_review", project_root=str(project_root))
    by_name = {artifact.get("name"): artifact for artifact in artifacts if artifact.get("name") in REQUIRED_REVIEW_ARTIFACTS}
    missing = [name for name in REQUIRED_REVIEW_ARTIFACTS if name not in by_name]
    if missing:
        raise FileNotFoundError(f"Missing review artifacts: {', '.join(missing)}")

    contents: dict[str, str] = {}
    selected: list[dict] = []
    for name in REQUIRED_REVIEW_ARTIFACTS:
        artifact = by_name[name]
        path = resolve_artifact_path(project_root, artifact["path"])
        if not path.is_file():
            raise FileNotFoundError(f"Review artifact file not found: {artifact['path']}")
        contents[name] = path.read_text(encoding="utf-8")
        selected.append(artifact)
    return contents, selected


def _stage_index(stage: str | None) -> int:
    if stage in CANONICAL_STAGE_SEQUENCE:
        return CANONICAL_STAGE_SEQUENCE.index(stage)
    return 0


def _allows_direct_proposal_entry(metadata: dict, state: dict) -> bool:
    """Return whether missing literature evidence is allowed for this workflow entry."""
    entry_stage = metadata.get("entry_point") or state.get("entry_point")
    current_stage = metadata.get("current_stage") or state.get("current_stage")
    return max(_stage_index(entry_stage), _stage_index(current_stage)) >= _stage_index("proposal")


def build_partial_review_inputs(metadata: dict, missing_message: str) -> tuple[dict[str, str], list[dict]]:
    """Build explicit no-literature placeholders for direct proposal entry."""
    goal = metadata.get("research_goal", "the current research goal") or "the current research goal"
    material = metadata.get("material", "the target system") or "the target system"
    return (
        {
            "review_summary.md": "\n".join([
                "- Literature review artifacts were not provided for this direct proposal entry.",
                f"- Proposal scope is based on user intent: {goal}.",
                f"- Target system from intake metadata: {material}.",
            ]),
            "gap_analysis.md": "\n".join([
                "- Literature evidence is missing and must be supplied or verified before evidence-backed claims are made.",
                "- Citation-backed assumptions are unavailable at proposal generation time.",
            ]),
        },
        [],
    )


def build_parameter_rows(metadata: dict) -> list[dict]:
    """Build proposal parameter table rows from workflow metadata."""
    rows = [
        {
            "parameter": "workflow_type",
            "value": metadata.get("workflow_type", "dft"),
            "source": "metadata",
            "notes": "Canonical workflow definition selected at intake.",
        },
        {
            "parameter": "software",
            "value": metadata.get("software", "vasp"),
            "source": "metadata",
            "notes": "Primary simulation software requested by the user.",
        },
        {
            "parameter": "material",
            "value": metadata.get("material", "Not specified"),
            "source": "metadata",
            "notes": "Target material or system under study.",
        },
    ]
    for key, value in metadata.get("parameters", {}).items():
        rows.append({
            "parameter": key,
            "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value),
            "source": "metadata.parameters",
            "notes": "User-provided structured parameter.",
        })
    return rows


def extract_gap_bullets(gap_analysis: str) -> list[str]:
    """Extract markdown bullet lines from gap analysis text."""
    return [line[2:].strip() for line in gap_analysis.splitlines() if line.startswith("- ")]


def _as_list(value) -> list:
    """Normalize optional metadata fields to a list."""
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _provided(value) -> bool:
    """Return whether a metadata value is meaningful enough for protocol intake."""
    return value not in (None, "", "Not specified")


def build_research_questions(metadata: dict, gap_analysis: str, parameter_rows: list[dict]) -> dict:
    """Build deterministic machine-readable research questions for Milestone C."""
    goal = metadata.get("research_goal", "the current research goal").strip() or "the current research goal"
    material = metadata.get("material", "the target system").strip() or "the target system"
    software = metadata.get("software", "vasp").strip() or "vasp"
    gap_bullets = extract_gap_bullets(gap_analysis)
    parameter_keys = [
        row["parameter"]
        for row in parameter_rows
        if row.get("parameter") not in {"workflow_type", "software", "material"}
    ]

    questions = [
        {
            "question_id": "rq_001",
            "category": "goal",
            "priority": "primary",
            "question": f"How should {goal} be investigated for {material} using {software}?",
            "source": "metadata.research_goal",
        }
    ]

    if parameter_keys:
        questions.append({
            "question_id": f"rq_{len(questions) + 1:03d}",
            "category": "execution",
            "priority": "primary",
            "question": "Which proposal parameters must be preserved through modeling and input generation?",
            "source": "metadata.parameters",
            "parameter_keys": parameter_keys,
        })

    for gap in gap_bullets:
        questions.append({
            "question_id": f"rq_{len(questions) + 1:03d}",
            "category": "validation",
            "priority": "secondary",
            "question": f"How will the workflow address this validation gap: {gap}?",
            "source": "review.gap_analysis",
        })

    return {
        "workflow_type": metadata.get("workflow_type", "dft"),
        "software": software,
        "material": material,
        "research_goal": goal,
        "questions": questions,
    }


def build_proposal_contract(
    metadata: dict,
    review_artifacts: list[dict],
    review_summary: str,
    gap_analysis: str,
    parameter_rows: list[dict],
    research_questions: dict,
    generated_at: str,
) -> dict:
    """Build the machine-readable proposal contract consumed by later stages."""
    workflow_type = metadata.get("workflow_type", "dft")
    software = metadata.get("software", "vasp")
    material = metadata.get("material", "Not specified")
    goal = metadata.get("research_goal", "Not specified")
    gap_bullets = extract_gap_bullets(gap_analysis)
    source_artifact_ids = [artifact["artifact_id"] for artifact in review_artifacts]
    literature_status = "provided" if source_artifact_ids else "not_provided"
    literature_summary = [
        line[2:].strip()
        for line in review_summary.splitlines()
        if line.startswith("- ")
    ][:5]

    return {
        "generated_at": generated_at,
        "workflow_type": workflow_type,
        "software": software,
        "material": material,
        "research_goal": goal,
        "source_artifact_ids": source_artifact_ids,
        "literature_evidence_summary": {
            "status": literature_status,
            "artifact_ids": source_artifact_ids,
            "summary_points": literature_summary,
            "open_questions": gap_bullets,
        },
        "calculation_plan": {
            "stage": "proposal",
            "recipe_or_tag": workflow_type,
            "software": software,
            "material": material,
            "planned_next_stages": ["modeling", "computation", "analysis_visualization", "writing"],
            "dry_run_first": True,
            "real_submit_requires_approval": True,
        },
        "parameter_rationale": [
            {
                "parameter": row["parameter"],
                "value": row["value"],
                "source": row["source"],
                "rationale": row["notes"],
            }
            for row in parameter_rows
        ],
        "decision_criteria": [
            {
                "criterion_id": "dc_001",
                "criterion": "The selected modeling and computation path preserves the stated research goal and material.",
                "evidence": ["research_goal", "material", "proposal.md"],
            },
            {
                "criterion_id": "dc_002",
                "criterion": "All real compute submissions remain blocked until dry-run evidence and approval are recorded.",
                "evidence": ["calculation_plan", "approval_triggers"],
            },
            {
                "criterion_id": "dc_003",
                "criterion": "Analysis and writing claims must trace back to registered literature, model, compute, analysis, or figure artifacts.",
                "evidence": ["source_artifact_ids", "artifact_lineage"],
            },
        ],
        "risk_register": [
            *([] if source_artifact_ids else [{
                "risk_id": "risk_000",
                "risk": "No registered literature review artifacts were available at proposal entry.",
                "mitigation": "Treat literature-dependent claims as unverified until review artifacts or citations are registered.",
                "severity": "high",
            }]),
            {
                "risk_id": "risk_001",
                "risk": "Proposal evidence may be incomplete if the literature stage only has metadata or notes.",
                "mitigation": "Mark inaccessible full text and keep claims limited to available evidence.",
                "severity": "medium",
            },
            {
                "risk_id": "risk_002",
                "risk": "Compute cost, license, or queue constraints may change the feasible calculation path.",
                "mitigation": "Keep resource assumptions explicit and require approval before real submit.",
                "severity": "medium",
            },
        ],
        "resource_assumptions": {
            "real_submit": False,
            "dry_run_first": True,
            "approval_triggers": ["large_resource_commitment", "licensed_or_proprietary_file_handling"],
            "resource_estimate_status": "proposal_level_assumption",
        },
        "research_question_ids": [item["question_id"] for item in research_questions.get("questions", [])],
    }


def build_protocol_contract(
    metadata: dict,
    review_artifacts: list[dict],
    gap_analysis: str,
    parameter_rows: list[dict],
    proposal_contract: dict,
    generated_at: str,
) -> dict:
    """Build a software-neutral protocol contract for downstream stage handoff."""
    workflow_type = metadata.get("workflow_type", "dft")
    software = metadata.get("software", "vasp")
    material = metadata.get("material", "Not specified")
    goal = metadata.get("research_goal", "Not specified")
    source_artifact_ids = [artifact["artifact_id"] for artifact in review_artifacts]
    literature_status = "provided" if source_artifact_ids else "not_provided"
    gap_bullets = extract_gap_bullets(gap_analysis)
    resource_assumptions = proposal_contract.get("resource_assumptions", {})
    approval_triggers = resource_assumptions.get(
        "approval_triggers",
        ["large_resource_commitment", "licensed_or_proprietary_file_handling"],
    )

    inputs = [
        {
            "input_id": "input_001",
            "name": "research_goal",
            "source": "metadata.research_goal",
            "required": True,
            "status": "provided" if _provided(goal) else "missing",
            "value": goal,
        },
        {
            "input_id": "input_002",
            "name": "material_or_system",
            "source": "metadata.material",
            "required": True,
            "status": "provided" if _provided(material) else "missing",
            "value": material,
        },
        {
            "input_id": "input_003",
            "name": "workflow_type",
            "source": "metadata.workflow_type",
            "required": True,
            "status": "provided" if _provided(workflow_type) else "missing",
            "value": workflow_type,
        },
        {
            "input_id": "input_004",
            "name": "software_preference",
            "source": "metadata.software",
            "required": False,
            "status": "provided" if _provided(software) else "unspecified",
            "value": software,
        },
        {
            "input_id": "input_005",
            "name": "literature_evidence",
            "source": "literature_review.artifacts",
            "required": False,
            "required_for": "evidence_backed_claims",
            "status": literature_status,
            "artifact_ids": source_artifact_ids,
        },
        {
            "input_id": "input_006",
            "name": "proposal_parameters",
            "source": "parameter_table.csv",
            "required": False,
            "status": "provided" if parameter_rows else "not_provided",
            "parameter_count": len(parameter_rows),
        },
    ]

    variables = [
        {
            "variable_id": f"var_{index:03d}",
            "name": row["parameter"],
            "value": row["value"],
            "source": row["source"],
            "role": "core_context" if row["parameter"] in {"workflow_type", "software", "material"} else "protocol_variable",
            "locked": row["parameter"] in {"workflow_type", "software", "material"},
            "notes": row.get("notes", ""),
        }
        for index, row in enumerate(parameter_rows, start=1)
    ]

    control_groups = []
    for index, item in enumerate(_as_list(metadata.get("control_groups") or metadata.get("controls")), start=1):
        if isinstance(item, dict):
            control_groups.append({
                "group_id": item.get("group_id") or f"control_{index:03d}",
                "name": item.get("name") or item.get("group") or f"control_{index:03d}",
                "description": item.get("description") or item.get("notes") or "",
                "source": item.get("source") or "metadata.control_groups",
                "status": item.get("status") or "provided",
            })
        else:
            control_groups.append({
                "group_id": f"control_{index:03d}",
                "name": str(item),
                "description": "",
                "source": "metadata.control_groups",
                "status": "provided",
            })
    if not control_groups:
        control_groups.append({
            "group_id": "control_001",
            "name": "baseline_or_reference",
            "description": "Define the baseline, reference, or negative-control comparison before computation.",
            "source": "proposal_protocol_default",
            "status": "needs_definition",
        })

    return {
        "schema_version": "protocol_contract.v1",
        "generated_at": generated_at,
        "objective": {
            "research_goal": goal,
            "material": material,
            "workflow_type": workflow_type,
            "software": software,
        },
        "evidence_limits": {
            "literature_status": literature_status,
            "source_artifact_ids": source_artifact_ids,
            "open_questions": gap_bullets,
            "claims_policy": (
                "Treat literature-dependent claims as unverified until review artifacts are registered."
                if literature_status == "not_provided"
                else "Limit claims to registered source artifacts and downstream artifacts."
            ),
        },
        "inputs": inputs,
        "variables": variables,
        "control_groups": control_groups,
        "ordered_steps": [
            {
                "step_id": "step_001",
                "stage": "proposal",
                "action": "Verify that protocol inputs, evidence limits, and user assumptions are explicit.",
                "acceptance_gate": "gate_001",
                "produces": ["protocol_contract.json"],
            },
            {
                "step_id": "step_002",
                "stage": "modeling",
                "action": "Translate objective, variables, and control groups into model or structure requirements.",
                "acceptance_gate": "gate_002",
                "produces": ["modeling_artifacts"],
            },
            {
                "step_id": "step_003",
                "stage": "computation",
                "action": "Map reviewed variables to candidate input files and dry-run validation checks.",
                "acceptance_gate": "gate_003",
                "produces": ["dry_run_evidence"],
            },
            {
                "step_id": "step_004",
                "stage": "computation",
                "action": "Request explicit approval before any real local, remote, or HPC execution.",
                "acceptance_gate": "gate_004",
                "produces": ["approval_record"],
            },
        ],
        "acceptance_gates": [
            {
                "gate_id": "gate_001",
                "name": "input_traceability",
                "required": True,
                "criteria": [
                    "Required inputs are provided or recorded as missing.",
                    "Literature evidence status is explicit.",
                    "Assumptions and open questions are visible to downstream stages.",
                ],
                "on_failure": "failure_001",
            },
            {
                "gate_id": "gate_002",
                "name": "modeling_handoff_ready",
                "required": True,
                "criteria": [
                    "Modeling inputs preserve the stated objective and material/system.",
                    "Control or reference comparisons are defined or explicitly pending.",
                ],
                "on_failure": "failure_002",
            },
            {
                "gate_id": "gate_003",
                "name": "dry_run_ready",
                "required": True,
                "criteria": [
                    "Candidate computation inputs are prepared for validation only.",
                    "Dry-run evidence can be registered before any real execution.",
                ],
                "on_failure": "failure_003",
            },
            {
                "gate_id": "gate_004",
                "name": "real_execution_approval",
                "required": True,
                "criteria": [
                    "Real compute remains blocked until dry-run evidence and approval are recorded.",
                    "Approval triggers are reviewed for resource, license, and remote-system risks.",
                ],
                "on_failure": "failure_004",
            },
        ],
        "dry_run_requirements": {
            "dry_run_first": True,
            "real_submit_requires_approval": True,
            "required_before_real_compute": [
                "registered_protocol_contract",
                "reviewed_modeling_or_input_artifacts",
                "dry_run_validation_evidence",
                "approval_gate_record",
            ],
            "disallowed_without_approval": [
                "real_local_compute",
                "remote_compute",
                "hpc_submit",
                "licensed_or_proprietary_file_transfer",
            ],
        },
        "failure_branches": [
            {
                "failure_id": "failure_001",
                "condition": "required_inputs_or_literature_evidence_missing",
                "response": "Record missing inputs and keep literature-dependent claims unverified.",
                "next_stage": "proposal",
            },
            {
                "failure_id": "failure_002",
                "condition": "modeling_requirements_ambiguous",
                "response": "Return to proposal/modeling clarification before generating compute inputs.",
                "next_stage": "modeling",
            },
            {
                "failure_id": "failure_003",
                "condition": "dry_run_validation_fails",
                "response": "Create a failure checkpoint and do not proceed to real execution.",
                "next_stage": "computation",
            },
            {
                "failure_id": "failure_004",
                "condition": "approval_missing_for_real_execution",
                "response": "Block real local, remote, or HPC execution until approval is recorded.",
                "next_stage": "computation",
            },
        ],
        "approval_triggers": approval_triggers,
        "handoff_outputs": [
            {
                "target_stage": "modeling",
                "required_artifacts": ["protocol_contract.json", "proposal_contract.json", "parameter_table.csv"],
                "purpose": "Build or select model inputs consistent with the proposal objective and variables.",
            },
            {
                "target_stage": "computation",
                "required_artifacts": ["protocol_contract.json", "modeling_artifacts", "dry_run_evidence"],
                "purpose": "Validate candidate inputs under dry-run rules before real execution approval.",
            },
        ],
    }


def build_proposal_markdown(
    metadata: dict,
    review_summary: str,
    gap_analysis: str,
    parameter_rows: list[dict],
    proposal_contract: dict,
    protocol_contract: dict,
) -> str:
    """Render a deterministic proposal markdown document."""
    gap_bullets = extract_gap_bullets(gap_analysis) or ["No explicit gaps were listed in the review stage."]
    summary_lines = [line for line in review_summary.splitlines() if line.startswith("- ")][:5]
    summary_section = summary_lines or ["- Review summary did not contain bullet evidence."]
    parameter_lines = [f"- {row['parameter']}: {row['value']}" for row in parameter_rows]
    decision_lines = [
        f"- {item['criterion_id']}: {item['criterion']}"
        for item in proposal_contract["decision_criteria"]
    ]
    risk_lines = [
        f"- {item['risk_id']}: {item['risk']} Mitigation: {item['mitigation']}"
        for item in proposal_contract["risk_register"]
    ]
    resource_lines = [
        f"- {key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value}"
        for key, value in proposal_contract["resource_assumptions"].items()
    ]
    source_lines = [f"- {artifact_id}" for artifact_id in proposal_contract["source_artifact_ids"]]
    protocol_gate_lines = [
        f"- {gate['gate_id']}: {gate['name']}"
        for gate in protocol_contract.get("acceptance_gates", [])
    ]

    return "\n".join([
        "# Proposal",
        "",
        "## Context",
        f"- Goal: {metadata.get('research_goal', 'Not specified')}",
        f"- Material: {metadata.get('material', 'Not specified')}",
        f"- Workflow type: {metadata.get('workflow_type', 'dft')}",
        f"- Software: {metadata.get('software', 'vasp')}",
        "",
        "## Review Inputs",
        *summary_section,
        "",
        "## Proposed Plan",
        f"- Start from the {metadata.get('workflow_type', 'dft')} workflow entry point defined in canonical metadata.",
        f"- Use {metadata.get('software', 'vasp')} as the primary simulation engine unless review findings force a change.",
        f"- Focus the next modeling decisions on {metadata.get('material', 'the target system')} with the user goal kept explicit.",
        "",
        "## Protocol Outline",
        "- Protocol contract: protocol_contract.json",
        f"- Dry-run first: {protocol_contract.get('dry_run_requirements', {}).get('dry_run_first', True)}",
        f"- Real execution requires approval: {protocol_contract.get('dry_run_requirements', {}).get('real_submit_requires_approval', True)}",
        "- Detailed machine-readable protocol fields are recorded in protocol_contract.json.",
        *protocol_gate_lines,
        "",
        "## Key Parameters",
        *parameter_lines,
        "",
        "## Validation Focus",
        *[f"- {bullet}" for bullet in gap_bullets],
        "",
        "## Decision Criteria",
        *decision_lines,
        "",
        "## Risk Register",
        *risk_lines,
        "",
        "## Resource Assumptions",
        *resource_lines,
        "",
        "## Source Artifact IDs",
        *source_lines,
        "",
    ])


def generate_proposal(workflow_dir: str, output_dir: str = None) -> dict:
    """Generate proposal.md, parameter_table.csv, and research_questions.json."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    try:
        review_contents, review_artifacts = load_review_artifacts(project_root)
    except FileNotFoundError as exc:
        if not _allows_direct_proposal_entry(metadata, state):
            return {"status": "error", "message": str(exc)}
        review_contents, review_artifacts = build_partial_review_inputs(metadata, str(exc))

    proposal_dir = Path(output_dir).expanduser() if output_dir else project_root / ".simflow" / "plans"
    if not proposal_dir.is_absolute():
        proposal_dir = project_root / proposal_dir
    proposal_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    parameter_rows = build_parameter_rows(metadata)
    research_questions = build_research_questions(metadata, review_contents["gap_analysis.md"], parameter_rows)
    research_questions["generated_at"] = generated_at
    proposal_contract = build_proposal_contract(
        metadata,
        review_artifacts,
        review_contents["review_summary.md"],
        review_contents["gap_analysis.md"],
        parameter_rows,
        research_questions,
        generated_at,
    )
    protocol_contract = build_protocol_contract(
        metadata,
        review_artifacts,
        review_contents["gap_analysis.md"],
        parameter_rows,
        proposal_contract,
        generated_at,
    )

    proposal_path = proposal_dir / "proposal.md"
    parameter_table_path = proposal_dir / "parameter_table.csv"
    research_questions_path = proposal_dir / "research_questions.json"
    proposal_contract_path = proposal_dir / "proposal_contract.json"
    protocol_contract_path = proposal_dir / "protocol_contract.json"
    proposal_content = build_proposal_markdown(
        metadata,
        review_contents["review_summary.md"],
        review_contents["gap_analysis.md"],
        parameter_rows,
        proposal_contract,
        protocol_contract,
    )
    proposal_path.write_text(proposal_content, encoding="utf-8")
    with parameter_table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["parameter", "value", "source", "notes"])
        writer.writeheader()
        writer.writerows(parameter_rows)
    research_questions_path.write_text(json.dumps(research_questions, indent=2, ensure_ascii=False), encoding="utf-8")
    proposal_contract_path.write_text(json.dumps(proposal_contract, indent=2, ensure_ascii=False), encoding="utf-8")
    protocol_contract_path.write_text(json.dumps(protocol_contract, indent=2, ensure_ascii=False), encoding="utf-8")

    proposal_registry_path = str(proposal_path.resolve().relative_to(project_root)) if proposal_path.resolve().is_relative_to(project_root) else str(proposal_path.resolve())
    parameter_registry_path = str(parameter_table_path.resolve().relative_to(project_root)) if parameter_table_path.resolve().is_relative_to(project_root) else str(parameter_table_path.resolve())
    questions_registry_path = str(research_questions_path.resolve().relative_to(project_root)) if research_questions_path.resolve().is_relative_to(project_root) else str(research_questions_path.resolve())
    contract_registry_path = str(proposal_contract_path.resolve().relative_to(project_root)) if proposal_contract_path.resolve().is_relative_to(project_root) else str(proposal_contract_path.resolve())
    protocol_registry_path = str(protocol_contract_path.resolve().relative_to(project_root)) if protocol_contract_path.resolve().is_relative_to(project_root) else str(protocol_contract_path.resolve())
    parent_artifacts = [artifact["artifact_id"] for artifact in review_artifacts]

    proposal_artifact = register_artifact(
        "proposal.md",
        "proposal",
        "proposal",
        project_root=str(project_root),
        path=proposal_registry_path,
        parent_artifacts=parent_artifacts,
        parameters={"parameter_count": len(parameter_rows)},
        software=metadata.get("software"),
        metadata={"evidence_key": "proposal"},
    )
    parameter_artifact = register_artifact(
        "parameter_table.csv",
        "parameter_table",
        "proposal",
        project_root=str(project_root),
        path=parameter_registry_path,
        parent_artifacts=[proposal_artifact["artifact_id"]],
        parameters={"parameter_count": len(parameter_rows)},
        software=metadata.get("software"),
        metadata={"evidence_key": "parameter_rationale"},
    )
    research_questions_artifact = register_artifact(
        "research_questions.json",
        "research_questions",
        "proposal",
        project_root=str(project_root),
        path=questions_registry_path,
        parent_artifacts=[proposal_artifact["artifact_id"], parameter_artifact["artifact_id"]],
        parameters={"question_count": len(research_questions["questions"])},
        software=metadata.get("software"),
        metadata={"evidence_key": "research_questions"},
    )
    proposal_contract_artifact = register_artifact(
        "proposal_contract.json",
        "proposal_contract",
        "proposal",
        project_root=str(project_root),
        path=contract_registry_path,
        parent_artifacts=[
            proposal_artifact["artifact_id"],
            parameter_artifact["artifact_id"],
            research_questions_artifact["artifact_id"],
        ],
        parameters={"decision_criteria_count": len(proposal_contract["decision_criteria"])},
        software=metadata.get("software"),
        metadata={"evidence_keys": ["calculation_plan", "resource_estimate", "risk_register"]},
    )
    protocol_contract_artifact = register_artifact(
        "protocol_contract.json",
        "protocol_contract",
        "proposal",
        project_root=str(project_root),
        path=protocol_registry_path,
        parent_artifacts=[
            proposal_artifact["artifact_id"],
            parameter_artifact["artifact_id"],
            research_questions_artifact["artifact_id"],
            proposal_contract_artifact["artifact_id"],
        ],
        parameters={
            "step_count": len(protocol_contract["ordered_steps"]),
            "gate_count": len(protocol_contract["acceptance_gates"]),
        },
        software=metadata.get("software"),
        metadata={"evidence_keys": ["ordered_steps", "acceptance_gates", "dry_run_requirements"]},
    )

    return {
        "status": "success",
        "generated_at": generated_at,
        "output_files": {
            "proposal": str(proposal_path),
            "parameter_table": str(parameter_table_path),
            "research_questions": str(research_questions_path),
            "proposal_contract": str(proposal_contract_path),
            "protocol_contract": str(protocol_contract_path),
        },
        "artifacts": [
            proposal_artifact,
            parameter_artifact,
            research_questions_artifact,
            proposal_contract_artifact,
            protocol_contract_artifact,
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate proposal artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output-dir", help="Optional output directory for proposal artifacts")
    add_helper_recording_args(parser, default_stage="proposal")
    args = parser.parse_args()

    try:
        result = generate_proposal(args.workflow_dir, args.output_dir)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="generate_proposal",
            output_paths=list(result.get("output_files", {}).values()),
        )
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
