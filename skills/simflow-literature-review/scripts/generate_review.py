#!/usr/bin/env python3
"""Generate review summary and gap analysis artifacts from the literature matrix."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.artifact import list_artifacts, register_artifact
from runtime.lib.state import read_state



def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path



def resolve_artifact_path(project_root: Path, artifact_path: str) -> Path:
    """Resolve a registry artifact path against the project root."""
    path = Path(artifact_path).expanduser()
    return path if path.is_absolute() else project_root / path



def load_latest_literature_matrix(project_root: Path) -> tuple[dict, dict]:
    """Load the latest registered literature matrix artifact."""
    artifacts = list_artifacts(stage="literature", project_root=str(project_root))
    candidates = [artifact for artifact in artifacts if artifact.get("name") == "literature_matrix.json" and artifact.get("path")]
    if not candidates:
        raise FileNotFoundError("No literature matrix artifact found")

    artifact = candidates[-1]
    path = resolve_artifact_path(project_root, artifact["path"])
    if not path.is_file():
        raise FileNotFoundError(f"Literature matrix file not found: {artifact['path']}")
    return json.loads(path.read_text(encoding="utf-8")), artifact



def build_review_summary(matrix: dict, metadata: dict) -> str:
    """Render a deterministic markdown review summary."""
    coverage_lines = [f"- {source_type}: {count}" for source_type, count in matrix.get("source_counts", {}).items()]
    evidence_lines = [
        f"- {row['source_id']} ({row['source_type']}): {row['label']} — {row['locator'] or 'manual note'}"
        for row in matrix.get("rows", [])
    ] or ["- No literature sources captured yet"]
    note_rows = [row for row in matrix.get("rows", []) if row.get("source_type") == "note" and row.get("notes")]
    observations = [f"- {row['notes']}" for row in note_rows] or ["- No manual synthesis notes were captured"]

    return "\n".join([
        "# Review Summary",
        "",
        "## Context",
        f"- Goal: {metadata.get('research_goal', 'Not specified')}",
        f"- Material: {metadata.get('material', 'Not specified')}",
        f"- Sources reviewed: {matrix.get('row_count', 0)}",
        "",
        "## Source Coverage",
        *coverage_lines,
        "",
        "## Evidence Inventory",
        *evidence_lines,
        "",
        "## Review Observations",
        *observations,
        "",
    ])



def build_gap_analysis(matrix: dict, metadata: dict) -> str:
    """Render a deterministic markdown gap analysis."""
    counts = matrix.get("source_counts", {})
    gaps = []
    if matrix.get("row_count", 0) < 3:
        gaps.append("Expand the source pool beyond the current seed set before proposal freeze.")
    if counts.get("doi", 0) == 0:
        gaps.append("Add DOI-backed entries so later stages can trace stable citations.")
    if counts.get("bibtex", 0) == 0:
        gaps.append("Capture at least one BibTeX source for reusable bibliography metadata.")
    note_rows = [row for row in matrix.get("rows", []) if row.get("source_type") == "note" and row.get("notes")]
    if not note_rows:
        gaps.append("Record manual screening notes to make the review rationale auditable.")
    else:
        gaps.extend(f"Follow up on manual note: {row['notes']}" for row in note_rows)

    if not gaps:
        gaps.append("No immediate literature coverage gaps were detected from the current source bundle.")

    return "\n".join([
        "# Gap Analysis",
        "",
        "## Context",
        f"- Goal: {metadata.get('research_goal', 'Not specified')}",
        f"- Material: {metadata.get('material', 'Not specified')}",
        "",
        "## Identified Gaps",
        *[f"- {gap}" for gap in gaps],
        "",
    ])



def generate_review(workflow_dir: str, output_dir: str = None) -> dict:
    """Generate review summary and gap analysis from the registered literature matrix."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    try:
        matrix, matrix_artifact = load_latest_literature_matrix(project_root)
    except FileNotFoundError as exc:
        return {"status": "error", "message": str(exc)}

    review_dir = Path(output_dir).expanduser() if output_dir else project_root / ".simflow" / "reports" / "review"
    if not review_dir.is_absolute():
        review_dir = project_root / review_dir
    review_dir.mkdir(parents=True, exist_ok=True)

    summary_path = review_dir / "review_summary.md"
    gap_path = review_dir / "gap_analysis.md"
    summary_content = build_review_summary(matrix, metadata)
    gap_content = build_gap_analysis(matrix, metadata)
    summary_path.write_text(summary_content, encoding="utf-8")
    gap_path.write_text(gap_content, encoding="utf-8")

    summary_registry_path = str(summary_path.resolve().relative_to(project_root)) if summary_path.resolve().is_relative_to(project_root) else str(summary_path.resolve())
    gap_registry_path = str(gap_path.resolve().relative_to(project_root)) if gap_path.resolve().is_relative_to(project_root) else str(gap_path.resolve())

    parent_artifacts = [matrix_artifact["artifact_id"]]
    summary_artifact = register_artifact(
        "review_summary.md",
        "review_summary",
        "review",
        project_root=str(project_root),
        path=summary_registry_path,
        parent_artifacts=parent_artifacts,
        parameters={"row_count": matrix.get("row_count", 0)},
        software=metadata.get("software"),
    )
    gap_artifact = register_artifact(
        "gap_analysis.md",
        "gap_analysis",
        "review",
        project_root=str(project_root),
        path=gap_registry_path,
        parent_artifacts=parent_artifacts,
        parameters={"row_count": matrix.get("row_count", 0)},
        software=metadata.get("software"),
    )

    return {
        "status": "success",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_files": {
            "review_summary": str(summary_path),
            "gap_analysis": str(gap_path),
        },
        "artifacts": [summary_artifact, gap_artifact],
    }



def main():
    parser = argparse.ArgumentParser(description="Generate review summary artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output-dir", help="Optional output directory for review artifacts")
    args = parser.parse_args()

    try:
        result = generate_review(args.workflow_dir, args.output_dir)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
