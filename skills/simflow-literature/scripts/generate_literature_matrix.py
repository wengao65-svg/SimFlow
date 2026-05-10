#!/usr/bin/env python3
"""Generate literature matrix artifacts from canonical research sources."""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.artifact import register_artifact
from runtime.lib.state import read_state
from runtime.lib.utils import generate_id


EMPTY_SOURCE_BUNDLE = {
    "bundle_version": "1.0",
    "counts": {"pdf": 0, "bibtex": 0, "doi": 0, "note": 0},
    "total_items": 0,
    "items": [],
}



def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path



def build_literature_rows(research_sources: dict, metadata: dict) -> list[dict]:
    """Build matrix rows from the normalized research-source bundle."""
    rows = []
    for item in research_sources.get("items", []):
        rows.append({
            "source_id": item["source_id"],
            "source_type": item["type"],
            "label": item.get("label", ""),
            "locator": item.get("path") or item.get("doi") or "",
            "notes": item.get("text", "") if item.get("type") == "note" else "",
            "research_goal": metadata.get("research_goal", ""),
            "material": metadata.get("material", ""),
        })
    return rows



def resolve_output_dir(project_root: Path, output_dir: str | None) -> Path:
    """Resolve the output directory for literature artifacts."""
    if not output_dir:
        return project_root / ".simflow" / "artifacts" / "literature"
    path = Path(output_dir).expanduser()
    return path if path.is_absolute() else project_root / path



def generate_literature_matrix(workflow_dir: str, output_dir: str = None) -> dict:
    """Generate literature matrix JSON and CSV artifacts."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    research_sources = metadata.get("research_sources") or EMPTY_SOURCE_BUNDLE
    rows = build_literature_rows(research_sources, metadata)

    matrix = {
        "matrix_id": generate_id("litmatrix"),
        "workflow_id": state.get("workflow_id", metadata.get("workflow_id", "unknown")),
        "workflow_type": metadata.get("workflow_type", state.get("workflow_type", "dft")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_goal": metadata.get("research_goal", "Not specified"),
        "material": metadata.get("material", "Not specified"),
        "software": metadata.get("software", "vasp"),
        "source_counts": research_sources.get("counts", EMPTY_SOURCE_BUNDLE["counts"]),
        "row_count": len(rows),
        "rows": rows,
    }

    literature_dir = resolve_output_dir(project_root, output_dir)
    literature_dir.mkdir(parents=True, exist_ok=True)
    json_path = literature_dir / "literature_matrix.json"
    csv_path = literature_dir / "literature_matrix.csv"

    json_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_id", "source_type", "label", "locator", "notes", "research_goal", "material"],
        )
        writer.writeheader()
        writer.writerows(rows)

    json_registry_path = str(json_path.resolve().relative_to(project_root)) if json_path.resolve().is_relative_to(project_root) else str(json_path.resolve())
    csv_registry_path = str(csv_path.resolve().relative_to(project_root)) if csv_path.resolve().is_relative_to(project_root) else str(csv_path.resolve())

    json_artifact = register_artifact(
        "literature_matrix.json",
        "literature_matrix",
        "literature",
        project_root=str(project_root),
        path=json_registry_path,
        parameters={"row_count": len(rows)},
        software=metadata.get("software"),
    )
    csv_artifact = register_artifact(
        "literature_matrix.csv",
        "literature_matrix_csv",
        "literature",
        project_root=str(project_root),
        path=csv_registry_path,
        parent_artifacts=[json_artifact["artifact_id"]],
        parameters={"row_count": len(rows)},
        software=metadata.get("software"),
    )

    return {
        "status": "success",
        "matrix": matrix,
        "output_files": {
            "json": str(json_path),
            "csv": str(csv_path),
        },
        "artifacts": [json_artifact, csv_artifact],
    }



def main():
    parser = argparse.ArgumentParser(description="Generate literature matrix artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output-dir", help="Optional output directory for literature artifacts")
    args = parser.parse_args()

    try:
        result = generate_literature_matrix(args.workflow_dir, args.output_dir)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
