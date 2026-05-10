#!/usr/bin/env python3
"""Generate proposal artifacts from registered review outputs."""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.artifact import list_artifacts, register_artifact
from runtime.lib.state import read_state


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
    artifacts = list_artifacts(stage="review", project_root=str(project_root))
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


def build_proposal_markdown(metadata: dict, review_summary: str, gap_analysis: str, parameter_rows: list[dict]) -> str:
    """Render a deterministic proposal markdown document."""
    gap_bullets = extract_gap_bullets(gap_analysis) or ["No explicit gaps were listed in the review stage."]
    summary_lines = [line for line in review_summary.splitlines() if line.startswith("- ")][:5]
    summary_section = summary_lines or ["- Review summary did not contain bullet evidence."]
    parameter_lines = [f"- {row['parameter']}: {row['value']}" for row in parameter_rows]

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

    proposal_path = proposal_dir / "proposal.md"
    parameter_table_path = proposal_dir / "parameter_table.csv"
    research_questions_path = proposal_dir / "research_questions.json"
    proposal_content = build_proposal_markdown(
        metadata,
        review_contents["review_summary.md"],
        review_contents["gap_analysis.md"],
        parameter_rows,
    )
    proposal_path.write_text(proposal_content, encoding="utf-8")
    with parameter_table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["parameter", "value", "source", "notes"])
        writer.writeheader()
        writer.writerows(parameter_rows)
    research_questions_path.write_text(json.dumps(research_questions, indent=2, ensure_ascii=False), encoding="utf-8")

    proposal_registry_path = str(proposal_path.resolve().relative_to(project_root)) if proposal_path.resolve().is_relative_to(project_root) else str(proposal_path.resolve())
    parameter_registry_path = str(parameter_table_path.resolve().relative_to(project_root)) if parameter_table_path.resolve().is_relative_to(project_root) else str(parameter_table_path.resolve())
    questions_registry_path = str(research_questions_path.resolve().relative_to(project_root)) if research_questions_path.resolve().is_relative_to(project_root) else str(research_questions_path.resolve())
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
    )

    return {
        "status": "success",
        "generated_at": generated_at,
        "output_files": {
            "proposal": str(proposal_path),
            "parameter_table": str(parameter_table_path),
            "research_questions": str(research_questions_path),
        },
        "artifacts": [proposal_artifact, parameter_artifact, research_questions_artifact],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate proposal artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output-dir", help="Optional output directory for proposal artifacts")
    args = parser.parse_args()

    try:
        result = generate_proposal(args.workflow_dir, args.output_dir)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
