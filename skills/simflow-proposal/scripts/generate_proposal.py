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


def build_proposal_markdown(
    metadata: dict,
    review_summary: str,
    gap_analysis: str,
    parameter_rows: list[dict],
    proposal_contract: dict,
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
        return {"status": "error", "message": str(exc)}

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

    proposal_path = proposal_dir / "proposal.md"
    parameter_table_path = proposal_dir / "parameter_table.csv"
    research_questions_path = proposal_dir / "research_questions.json"
    proposal_contract_path = proposal_dir / "proposal_contract.json"
    proposal_content = build_proposal_markdown(
        metadata,
        review_contents["review_summary.md"],
        review_contents["gap_analysis.md"],
        parameter_rows,
        proposal_contract,
    )
    proposal_path.write_text(proposal_content, encoding="utf-8")
    with parameter_table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["parameter", "value", "source", "notes"])
        writer.writeheader()
        writer.writerows(parameter_rows)
    research_questions_path.write_text(json.dumps(research_questions, indent=2, ensure_ascii=False), encoding="utf-8")
    proposal_contract_path.write_text(json.dumps(proposal_contract, indent=2, ensure_ascii=False), encoding="utf-8")

    proposal_registry_path = str(proposal_path.resolve().relative_to(project_root)) if proposal_path.resolve().is_relative_to(project_root) else str(proposal_path.resolve())
    parameter_registry_path = str(parameter_table_path.resolve().relative_to(project_root)) if parameter_table_path.resolve().is_relative_to(project_root) else str(parameter_table_path.resolve())
    questions_registry_path = str(research_questions_path.resolve().relative_to(project_root)) if research_questions_path.resolve().is_relative_to(project_root) else str(research_questions_path.resolve())
    contract_registry_path = str(proposal_contract_path.resolve().relative_to(project_root)) if proposal_contract_path.resolve().is_relative_to(project_root) else str(proposal_contract_path.resolve())
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

    return {
        "status": "success",
        "generated_at": generated_at,
        "output_files": {
            "proposal": str(proposal_path),
            "parameter_table": str(parameter_table_path),
            "research_questions": str(research_questions_path),
            "proposal_contract": str(proposal_contract_path),
        },
        "artifacts": [proposal_artifact, parameter_artifact, research_questions_artifact, proposal_contract_artifact],
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
